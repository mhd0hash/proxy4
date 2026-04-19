from flask import Flask, request, Response, jsonify
from urllib.parse import urlparse
import requests
import re

app = Flask(__name__)

# هدف را به وب تلگرام تغییر می‌دهیم
TARGET_URL = "https://web.telegram.org/k/"

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    try:
        # تجزیه URL هدف برای استخراج هاست
        target_url_parsed = urlparse(TARGET_URL)
        target_host = target_url_parsed.netloc # 'web.telegram.org'

        # ساخت URL کامل مقصد
        # اگر path خالی باشد (یعنی درخواست اصلی به '/' باشد)، از TARGET_URL استفاده می‌کنیم
        # اگر path وجود داشته باشد، آن را به انتهای TARGET_URL اضافه می‌کنیم
        full_target_url = f"{TARGET_URL.rstrip('/')}/{path}" if path else TARGET_URL.rstrip('/')

        # دریافت هدرهای درخواست اصلی
        headers = {}
        for key, value in request.headers.items():
            # فیلتر کردن هدرهای ناخواسته برای درخواست به سرور مقصد
            # هدر Host توسط requests به درستی مدیریت می‌شود
            # هدرهای مربوط به اطلاعات پراکسی و اتصال را حذف می‌کنیم
            if key not in ['Host', 'X-Forwarded-For', 'X-Forwarded-Proto', 'X-Real-IP', 'Connection', 'Upgrade', 'Content-Length', 'Transfer-Encoding', 'Sec-WebSocket-Key', 'Sec-WebSocket-Version', 'Sec-WebSocket-Accept', 'Sec-WebSocket-Extensions']:
                 headers[key] = value

        # تنظیم هدر Host برای سرور مقصد (وب تلگرام)
        headers['Host'] = target_host

        # آماده‌سازی URL برای ارسال با requests
        # اطمینان حاصل می‌کنیم که query string اصلی حفظ شود
        request_url_parsed = urlparse(request.url)
        query_string = request.query_string.decode('utf-8')

        # بازسازی URL کامل برای ارسال به تلگرام
        # از URL هدف به عنوان مبنا استفاده می‌کنیم تا scheme و netloc درست باشند
        url_to_fetch = urlparse(TARGET_URL).scheme + "://" + target_host + request_url_parsed.path
        if query_string:
             url_to_fetch += "?" + query_string

        # استفاده از requests برای ارسال درخواست به سرور مقصد
        session = requests.Session()
        session.headers.update(headers)

        # درخواست به وب تلگرام
        resp = session.request(
            method=request.method,
            url=url_to_fetch,
            data=request.get_data(),
            cookies=request.cookies,
            stream=True, # برای مدیریت بهتر پاسخ‌های بزرگ یا استریم
            allow_redirects=False # مدیریت دستی ریدایرکت‌ها در صورت نیاز
        )

        # آماده‌سازی هدرهای پاسخ برای ارسال به کلاینت
        response_headers = {}
        for key, value in resp.headers.items():
            # فیلتر کردن هدرهایی که نباید به کلاینت برگردند
            if key not in ['Content-Encoding', 'Transfer-Encoding', 'Connection', 'Content-Length', 'Set-Cookie']: # Set-Cookie را باید مدیریت کنیم
                response_headers[key] = value

        # مدیریت کوکی‌ها: اگر سرور مقصد کوکی تنظیم کند، باید به کلاینت برگردانیم
        if 'Set-Cookie' in resp.headers:
             response_headers['Set-Cookie'] = resp.headers['Set-Cookie']


        # ایجاد یک پاسخ جریانی (streaming response)
        def generate():
            # در صورت نیاز به مدیریت بهتر استریم، می‌توان این بخش را پیچیده‌تر کرد
            # فعلا کل محتوا را یکجا برمی‌گردانیم
            yield resp.content

        # بازگرداندن پاسخ به کلاینت با وضعیت و هدرهای مناسب
        return Response(generate(), status=resp.status_code, headers=response_headers)

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request to target URL {TARGET_URL} failed: {e}")
        # در صورت بروز خطا در اتصال به تلگرام، پاسخ مناسب برمی‌گردانیم
        return jsonify({"error": "Failed to connect to the target server (Telegram Web)", "details": str(e)}), 503
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")
        # مدیریت خطاهای پیش‌بینی نشده
        return jsonify({"error": "An internal server error occurred", "details": str(e)}), 500

if __name__ == '__main__':
    # این بلاک برای اجرای محلی است. Vercel خودش سرور را مدیریت می‌کند.
    # برای تست محلی: flask run --host=0.0.0.0
    pass

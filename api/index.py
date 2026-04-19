import os
import requests
from flask import Flask, request, Response

app = Flask(__name__)

# آدرس هدف که فقط تلگرام وب است
TARGET_URL = "https://web.telegram.org/k/"

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE'])
def proxy(path):
    # بررسی می‌کنیم که آیا URL درخواستی، زیرمجموعه TARGET_URL است یا خود TARGET_URL است.
    # این بررسی به صورت ساده انجام شده و ممکن است نیاز به دقت بیشتری داشته باشد
    # بسته به ساختار URL های تلگرام.
    
    # ساخت URL کامل بر اساس مسیر درخواستی
    full_requested_url = TARGET_URL + path.lstrip('/')
    
    # اگر مسیر خالی بود، فقط از TARGET_URL استفاده کن
    if path == "":
        full_requested_url = TARGET_URL
        
    # این شرط را برای اطمینان بیشتر اضافه می‌کنیم که فقط به دامنه تلگرام هدایت شویم
    # توجه: ساختار URL های تلگرام ممکن است پیچیده باشد و این شرط ممکن است نیاز به تنظیم دقیق‌تری داشته باشد.
    if not full_requested_url.startswith("https://web.telegram.org/k/"):
         return Response("Access Denied: Only web.telegram.org/k/ is allowed.", status=403)

    try:
        # استفاده از URL کامل که از TARGET_URL ساخته شده
        req_url = full_requested_url
        
        headers = request.headers.to_dict()

        # حذف هدرهای خاصی که ممکن است در پراکسی مشکل ایجاد کنند یا نیازی به ارسال نباشند
        headers.pop('Host', None)
        headers.pop('X-Forwarded-For', None)
        headers.pop('X-Real-IP', None)
        headers.pop('Connection', None)
        # هدرهای مرتبط با Vercel که ممکن است توسط Vercel اضافه شده باشند و نیازی به ارسال به سرور مقصد نباشند
        headers.pop('X-Vercel-Id', None)
        headers.pop('X-Vercel-Proxy-Reason', None)
        headers.pop('X-Vercel-Cache-Tag', None)
        
        # تنظیم هدر Host برای دامنه صحیح تلگرام
        headers['Host'] = 'web.telegram.org'

        resp = requests.request(
            method=request.method,
            url=req_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False # اجازه ندهیم که درخواست‌های بازگردانی خودکار انجام شوند، خودمان مدیریت می‌کنیم
        )

        # کپی کردن هدرهای پاسخ از سرور اصلی به پاسخ پراکسی
        response_headers = {}
        for key, value in resp.headers.items():
            # فیلتر کردن هدرهایی که ممکن است در پراکسی مشکل ایجاد کنند یا نیازی به ارسال نباشند
            if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection', 'content-security-policy']:
                response_headers[key] = value
        
        # اضافه کردن هدر CSP برای تلگرام، چون ممکن است توسط پراکسی حذف شده باشد
        # توجه: تنظیمات CSP ممکن است پیچیده باشد و این یک تنظیم ساده است.
        # اگر تلگرام مشکلی در اجرای CSP داشت، این هدر را حذف کنید.
        # response_headers['Content-Security-Policy'] = "default-src 'self'; connect-src 'self' https://*; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://*; font-src 'self' data:; frame-src 'self' blob:;"
        
        response = Response(resp.content, resp.status_code, response_headers)
        
        # مدیریت کوکی‌ها: برخی کوکی‌ها ممکن است برای تلگرام لازم باشند.
        # به طور پیش‌فرض کوکی‌ها منتقل می‌شوند، اما اگر مشکلی بود، اینجا قابل تنظیم است.
        
        return response

    except requests.exceptions.MissingSchema:
        return Response("Invalid URL: Missing schema (http:// or https://)", status=400)
    except requests.exceptions.InvalidURL:
        return Response("Invalid URL provided.", status=400)
    except requests.exceptions.ConnectionError:
        return Response("Connection Error: Could not connect to the target server.", status=503)
    except requests.exceptions.Timeout:
        return Response("Request Timed Out.", status=504)
    except requests.exceptions.RequestException as e:
        return Response(f"An error occurred during the request: {str(e)}", status=500)
    except Exception as e:
        return Response(f"An unexpected error occurred: {str(e)}", status=500)

# اجرای اپلیکیشن Flask در پورت مشخص شده توسط Vercel یا پورت 8080 به عنوان پیش‌فرض
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)

import os
import requests
from flask import Flask, request, Response

app = Flask(__name__)

# آدرس هدف که فقط گوگل است
TARGET_URL = "http://www.google.com"

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE'])
def proxy(path):
    # اگر مسیر خالی بود، فقط TARGET_URL را استفاده کن
    # در غیر این صورت، مسیر درخواستی را به TARGET_URL اضافه کن
    if path == "":
        req_url = TARGET_URL
    else:
        # اطمینان حاصل کنید که بین TARGET_URL و path یک "/" وجود دارد
        # برخی URL ها ممکن است به / ختم شوند یا نه.
        # این روش کمی قوی‌تر است:
        req_url = f"{TARGET_URL.rstrip('/')}/{path.lstrip('/')}"

    try:
        headers = request.headers.to_dict()

        # حذف هدرهای غیرضروری که ممکن است باعث مشکل شوند
        headers.pop('Host', None)
        headers.pop('X-Forwarded-For', None)
        headers.pop('X-Real-IP', None)
        headers.pop('Connection', None)
        # هدرهای خاص Vercel را نیز حذف می‌کنیم
        headers.pop('X-Vercel-Id', None)
        headers.pop('X-Vercel-Proxy-Reason', None)
        headers.pop('X-Vercel-Cache-Tag', None)

        # اضافه کردن هدر Host درست
        headers['Host'] = 'www.google.com' # این هدر برای گوگل مهم است

        resp = requests.request(
            method=request.method,
            url=req_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False # جلوگیری از ریدایرکت خودکار
        )

        # کپی کردن هدرهای پاسخ
        response_headers = {}
        for key, value in resp.headers.items():
            # فیلتر کردن هدرهایی که ممکن است مشکل ساز شوند
            # Content-Encoding و Transfer-Encoding ممکن است توسط requests مدیریت شوند
            if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection', 'content-security-policy', 'strict-transport-security']:
                response_headers[key] = value
        
        # اگر گوگل هدر CSP یا HSTS ارسال کند، ممکن است لازم باشد آنها را حذف کنیم
        # تا در سمت پراکسی مشکل ایجاد نشود، یا برعکس، ممکن است لازم باشد آنها را منتقل کنیم.
        # در حال حاضر آنها را حذف می‌کنیم.

        response = Response(resp.content, resp.status_code, response_headers)
        
        # مدیریت کوکی‌های دریافتی از گوگل
        # به طور پیش‌فرض کوکی‌ها کپی می‌شوند، اما اگر مشکلی بود، اینجا قابل تنظیم است.

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
        # برای خطاهای مربوط به requests
        return Response(f"An error occurred during the request: {str(e)}", status=500)
    except Exception as e:
        # برای خطاهای پیش‌بینی نشده دیگر
        return Response(f"An unexpected error occurred: {str(e)}", status=500)

# برای اجرای لوکال (اگر نیاز شد)
if __name__ == '__main__':
    # این پورت توسط Vercel تنظیم می‌شود، اما برای اجرای لوکال هم مفید است
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port) # debug=False برای محیط پروداکشن

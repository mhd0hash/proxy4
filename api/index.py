import os
import requests
from flask import Flask, request, Response

app = Flask(__name__)

TARGET_URL = "http://www.google.com" # فقط گوگل

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE'])
def proxy(path):
    # فقط اجازه دسترسی به google.com را بده
    if TARGET_URL not in request.url:
        return Response("Access Denied: Only google.com is allowed.", status=403)

    url_path = TARGET_URL + '/' + path
    if path == "": # اگر مسیر خالی بود، فقط TARGET_URL را استفاده کن
        url_path = TARGET_URL

    try:
        req_url = url_path
        headers = request.headers.to_dict()

        # حذف هدرهای غیرضروری که ممکن است باعث مشکل شوند
        headers.pop('Host', None)
        headers.pop('X-Forwarded-For', None)
        headers.pop('X-Real-IP', None)
        headers.pop('Connection', None)

        # اضافه کردن هدر Host درست
        headers['Host'] = 'www.google.com'

        resp = requests.request(
            method=request.method,
            url=req_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False)

        # کپی کردن هدرهای پاسخ
        response_headers = {}
        for key, value in resp.headers.items():
            # فیلتر کردن هدرهایی که ممکن است مشکل ساز شوند
            if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection']:
                response_headers[key] = value

        response = Response(resp.content, resp.status_code, response_headers)
        return response

    except requests.exceptions.RequestException as e:
        return Response(f"An error occurred: {str(e)}", status=500)
    except Exception as e:
        return Response(f"An unexpected error occurred: {str(e)}", status=500)

# برای اجرای لوکال (اگر نیاز شد)
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 8080)))

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
    if path == "":
        req_url = TARGET_URL
    else:
        req_url = f"{TARGET_URL.rstrip('/')}/{path.lstrip('/')}"

    try:
        # استخراج هدرها به روش صحیح در Flask
        headers = {}
        for header, value in request.headers.items():
            # انتقال هدرهای مورد نیاز و حذف موارد خاص
            if header.lower() not in ['host', 'x-forwarded-for', 'x-real-ip', 'connection',
                                     'x-vercel-id', 'x-vercel-proxy-reason', 'x-vercel-cache-tag']:
                headers[header] = value

        # اضافه کردن هدر Host درست
        headers['Host'] = 'www.google.com'

        resp = requests.request(
            method=request.method,
            url=req_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )

        # کپی کردن هدرهای پاسخ
        response_headers = {}
        for key, value in resp.headers.items():
            if key.lower() not in ['content-encoding', 'transfer-encoding', 'connection', 'content-security-policy', 'strict-transport-security']:
                response_headers[key] = value

        response = Response(resp.content, resp.status_code, response_headers)
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)

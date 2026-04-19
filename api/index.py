import os
import requests
from flask import Flask, request, Response
from urllib.parse import urlparse, urlunparse

app = Flask(__name__)

TARGET_URL = "http://www.google.com"

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD', 'TRACE'])
def proxy(path):
    try:
        # ساخت URL کامل مقصد با ترکیب TARGET_URL و path دریافتی
        # request.url شامل کل URL است، اما ما فقط به بخش path و query نیاز داریم
        # برای این کار، query string را به صورت دستی به path اضافه می‌کنیم اگر وجود داشته باشد
        full_url_from_request = request.url
        parsed_request_url = urlparse(full_url_from_request)

        # اگر مسیر خالی است، از TARGET_URL استفاده کن
        if path == "" and not parsed_request_url.query:
            req_url = TARGET_URL
        else:
            # ترکیب TARGET_URL با path و query string از درخواست اصلی
            # اطمینان حاصل کنید که query string به صورت صحیح اضافه می‌شود
            query_string = parsed_request_url.query
            base_target_url = TARGET_URL.rstrip('/')

            if path:
                 # اگر path وجود دارد، آن را به base_target_url اضافه کن
                req_url_parts = list(urlparse(base_target_url))
                req_url_parts[2] = f"{req_url_parts[2].rstrip('/')}/{path.lstrip('/')}" # path part
                
                # اضافه کردن query string اگر وجود دارد
                if query_string:
                    req_url_parts[4] = query_string # query part
                
                req_url = urlunparse(req_url_parts)

            elif query_string:
                 # اگر path خالی است ولی query string وجود دارد (مثلا درخواست ریشه با query)
                 req_url_parts = list(urlparse(base_target_url))
                 req_url_parts[4] = query_string
                 req_url = urlunparse(req_url_parts)
            else:
                 # اگر هم path و هم query خالی بودند
                 req_url = base_target_url


        # اطمینان حاصل کنید که req_url معتبر است (مثلا http://www.google.com)
        if not req_url.startswith(('http://', 'https://')):
             # اگر TARGET_URL هم schema نداشت، یک پیش‌فرض اضافه کن
             req_url = f"http://{req_url}"
             
        # اگر TARGET_URL فقط "www.google.com" بود و schema نداشت، حالا اضافه شده است
        # اگر TARGET_URL کامل بود (مثلا "http://www.google.com")، این خط تاثیری ندارد


        headers = {}
        for header, value in request.headers.items():
            if header.lower() not in ['host', 'x-forwarded-for', 'x-real-ip', 'connection',
                                     'x-vercel-id', 'x-vercel-proxy-reason', 'x-vercel-cache-tag']:
                headers[header] = value

        # مهم: هدر Host را بر اساس URL هدف تنظیم کنید
        parsed_target = urlparse(req_url)
        headers['Host'] = parsed_target.netloc if parsed_target.netloc else 'www.google.com'


        resp = requests.request(
            method=request.method,
            url=req_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )

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
        # برای خطاهای پیش‌بینی نشده دیگر، خطای دقیق را نمایش می‌دهیم
        return Response(f"An unexpected error occurred: {str(e)}", status=500)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)

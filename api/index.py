from flask import Flask, request, Response
import requests

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(path):
    try:
        # مقصد کامل (URL کامل)
        target_url = f"https://{path}"

        # انتقال هدرها (به جز host)
        headers = {key: value for key, value in request.headers if key.lower() != 'host'}

        # درخواست پروکسی
        proxied = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            params=request.args,
            data=request.get_data(),
            allow_redirects=False
        )

        # پاسخ را منتقل کن
        response = Response(proxied.content, proxied.status_code)
        for key, value in proxied.headers.items():
            if key.lower() not in ["content-encoding", "transfer-encoding", "connection"]:
                response.headers[key] = value

        # مجوز دسترسی (CORS)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"

        return response

    except Exception as e:
        return {"error": str(e)}, 500


def handler(request, response):
    return app(request.environ, response.start_response)

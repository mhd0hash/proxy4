from flask import Flask, request, Response, jsonify
from urllib.parse import urlparse, urlencode, parse_qs
import requests
import re

app = Flask(__name__)

#TARGET_URL = "https://web.telegram.org/k/"
TARGET_URL = "http://www.google.com" # یا هر URL دیگری که میخواهید

# Dictionary to store allowed hostnames
ALLOWED_HOSTS = {
    "google.com",
    "www.google.com",
    # Add other domains if needed, e.g., "web.telegram.org"
}

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def proxy(path):
    try:
        target_url_parsed = urlparse(TARGET_URL)
        target_host = target_url_parsed.netloc

        # Construct the full target URL for the request
        full_target_url = f"{TARGET_URL}/{path}" if path else TARGET_URL

        # Check if the requested URL is for the target host (or google for search)
        # Allow requests to the main TARGET_URL or google.com if path starts with 'search'
        request_host = urlparse(request.url).netloc
        parsed_request_path = urlparse(request.url).path

        # Check if the target URL is Google and the request is for search
        is_google_search = (target_host in ["www.google.com", "google.com"] and parsed_request_path.startswith('/search'))

        # We only proxy requests intended for our TARGET_URL or if it's a Google search request
        # This condition is a bit tricky and might need adjustment based on exact needs.
        # For now, let's simplify: if the request *originates* from our proxy domain, and it's not
        # an attempt to access something else directly, we forward it.
        # A more robust check is to ensure the *original* request was intended for our proxy.
        # Since Vercel handles routing to this function based on the proxy domain,
        # we can often just forward the request if it matches expected patterns.

        # Let's refine the logic: forward if it's the root or a path, and ensure we don't loop.
        # We will forward all requests to the TARGET_URL, but we need to handle headers carefully.

        headers = {}
        for key, value in request.headers.items():
            # Filter out problematic headers for the upstream request
            if key not in ['Host', 'X-Forwarded-For', 'X-Forwarded-Proto', 'X-Real-IP', 'Connection', 'Upgrade']:
                 headers[key] = value

        # Add or correct the Host header for the target server
        headers['Host'] = target_host

        # Prepare the URL to send the request to
        # If the request is for the root path, use TARGET_URL directly.
        # If there's a path, append it to TARGET_URL.
        # We need to handle query parameters correctly.
        final_target_url = urlparse(full_target_url)
        query_string = request.query_string.decode('utf-8')

        # Rebuild the URL with original path and query string
        # Ensure scheme and netloc are from TARGET_URL
        url_to_fetch = urlparse(TARGET_URL).scheme + "://" + urlparse(TARGET_URL).netloc + parsed_request_path
        if query_string:
             url_to_fetch += "?" + query_string


        # Use requests.Session for potential connection reuse
        session = requests.Session()
        session.headers.update(headers)

        resp = session.request(
            method=request.method,
            url=url_to_fetch,
            data=request.get_data(),
            cookies=request.cookies,
            stream=True, # Use stream=True for streaming the response
            allow_redirects=False # We will handle redirects manually if needed
        )

        # Prepare the response to be sent back to the client
        response_headers = {}
        for key, value in resp.headers.items():
            # Filter out headers that should not be sent back to the client
            if key not in ['Content-Encoding', 'Transfer-Encoding', 'Connection', 'Content-Length']:
                response_headers[key] = value

        # Create a streaming response
        def generate():
            yield resp.content # Initially yield all content, will refine if streaming needed

        return Response(generate(), status=resp.status_code, headers=response_headers)

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Request to target URL failed: {e}")
        return jsonify({"error": "Failed to connect to the target server", "details": str(e)}), 503
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal server error occurred", "details": str(e)}), 500

if __name__ == '__main__':
    # In Vercel, the server is run by the platform.
    # This block is typically for local testing.
    # Use 'flask run --host=0.0.0.0' for local testing.
    pass

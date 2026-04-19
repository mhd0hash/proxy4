import os
from flask import Flask, request, Response
import requests
import re

app = Flask(__name__)

@app.route('/<path:url_path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def handler(url_path):
    # The full URL requested by the client to the Vercel app
    full_request_url = request.url

    # Extract the part that comes after the Vercel app's domain.
    # This should be the target URL, potentially with scheme.
    # Example: If request is https://app.vercel.sh/http://google.com/path
    # base_url is https://app.vercel.sh
    # url_path might be "http://google.com/path"
    # We need to get the part after the Vercel domain.
    # A more robust way is to parse the incoming URL.
    try:
        # Get the Vercel app's base URL from request headers or infer it
        # For simplicity, let's assume the structure implies url_path is the target URL + path
        # Example: request.url = "https://proxy4-psi.vercel.app/http://google.com/search?q=test"
        # We need to extract "http://google.com/search?q=test"
        
        # Splitting by the first occurrence of the Vercel domain + '/' might be fragile.
        # A better approach: get the path relative to the Vercel app's root.
        # The 'url_path' parameter already gives us the part after the Vercel domain.
        target_url_from_path = url_path

        # --- CHECK AND FIX URL ---
        original_target_url = target_url_from_path # Store for potential error messages

        # Check if the path itself starts with http:// or https://
        if not re.match(r'^(http|https)://', target_url_from_path):
            # If not, it might be just a domain or a path without scheme.
            # We need to find the actual domain part.
            # Let's assume the first part before any '/' is the domain.
            parts = target_url_from_path.split('/', 1)
            domain_part = parts[0]
            path_part = parts[1] if len(parts) > 1 else ''

            # Check if the domain part looks like a domain (contains dots)
            # This is a heuristic and might need refinement
            if '.' in domain_part:
                # Assume it's a domain without scheme, prepend http://
                target_url = 'http://' + target_url_from_path
            else:
                # If it doesn't look like a domain, maybe it's an error or needs default Vercel handling.
                # Or perhaps the Vercel app itself is the target if nothing is provided?
                # For now, let's return an error if it's clearly not a URL.
                return Response(f"Invalid URL format: '{original_target_url}'. Expected format like 'http://example.com' or 'https://example.com'.", status=400)
        else:
            # It already has a scheme, use it as is.
            target_url = target_url_from_path

        # --- END CHECK AND FIX URL ---
        
        # Ensure we have a valid URL to request
        if not target_url or not re.match(r'^(http|https)://', target_url):
             return Response(f"Failed to construct a valid URL. Processed target: '{target_url}' from original path: '{original_target_url}'", status=400)


        # Prepare headers to forward
        excluded_headers = ['host', 'connection', 'transfer-encoding', 'content-length', 'accept-encoding', 'upgrade-insecure-requests', 'user-agent'] # Added more common excluded headers
        headers = {k: v for k, v in request.headers.items() if k.lower() not in excluded_headers}

        # Add Host header with the actual target host
        # Parse the target_url to get the hostname
        parsed_target_url = requests.utils.urlparse(target_url)
        if parsed_target_url.hostname:
            headers['Host'] = parsed_target_url.hostname
        else:
             # Fallback if parsing fails, though unlikely with the checks above
             return Response(f"Could not determine hostname for target URL: {target_url}", status=400)


        # Forward the request
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )

        # Prepare the response
        response_headers = {k: v for k, v in resp.headers.items() if k.lower() not in excluded_headers and k.lower() != 'content-encoding'} # Exclude content-encoding as requests handles it
        
        # Ensure CORS headers are present
        response_headers['Access-Control-Allow-Origin'] = '*'
        response_headers['Access-Control-Allow-Methods'] = '*' # Allow all methods for flexibility
        response_headers['Access-Control-Allow-Headers'] = '*' # Allow all headers


        # Create Flask response
        response = Response(resp.content, resp.status_code, response_headers)
        return response

    except requests.exceptions.MissingSchema:
        # This catch might be redundant with the re.match checks, but good as a fallback
        return Response(f"Invalid URL provided: '{original_target_url}'. It's missing the required 'http://' or 'https://' scheme.", status=400)
    except requests.exceptions.ConnectionError:
        return Response(f"Connection Error: Could not connect to '{target_url}'. Please check the URL.", status=500)
    except requests.exceptions.InvalidURL:
         return Response(f"Invalid URL: The URL '{target_url}' is not valid.", status=400)
    except requests.exceptions.RequestException as e:
        return Response(f"An unexpected error occurred during the request: {str(e)}", status=500)
    except Exception as e:
        # Catch any other unexpected errors
        return Response(f"An internal server error occurred: {str(e)}", status=500)


# For local development
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # When running locally, Vercel's routing doesn't apply directly.
    # You might need to simulate the path structure or test with curl.
    # Example local test: curl -L -X GET "http://localhost:5000/http://google.com"
    app.run(host='0.0.0.0', port=port, debug=True)

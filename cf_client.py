"""Cloudflare REST API v4 HTTP client."""

try:
    import requests
except ImportError:
    import sys
    print("✗ ERROR: 'requests' library is required. Install it with: pip install requests")
    sys.exit(1)

CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"

# Stable ID for the Cloudflare Managed Ruleset — sourced from:
# https://developers.cloudflare.com/waf/managed-rules/reference/cloudflare-managed-ruleset/
CF_MANAGED_RULESET_ID = "efb7b8c949ac4650a09736fc376e9aee"


class CloudflareClient:
    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{CLOUDFLARE_API_BASE}{path}"
        resp = self.session.request(method, url, timeout=30, **kwargs)
        try:
            return resp.json()
        except Exception:
            return {"success": False, "errors": [{"code": 0, "message": resp.text}]}

    def post(self, path: str, body: dict) -> dict:
        return self._request("POST", path, json=body)

    def patch(self, path: str, body: dict) -> dict:
        return self._request("PATCH", path, json=body)

    def put(self, path: str, body: dict) -> dict:
        return self._request("PUT", path, json=body)

    def delete(self, path: str) -> dict:
        return self._request("DELETE", path)

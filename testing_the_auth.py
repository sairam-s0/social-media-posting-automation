"""Standalone LinkedIn OAuth test. Run from the project root with the app CLOSED (it needs port 8000).

    python test_linkedin_oauth.py          # no PKCE, client_secret only (should work)
    python test_linkedin_oauth.py --pkce   # PKCE + client_secret (what your app does now)

Auth codes are single use, so run one variant at a time and compare results.
"""
import base64
import hashlib
import os
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

REDIRECT_URI = "http://127.0.0.1:8000/auth/linkedin/callback"
USE_PKCE = "--pkce" in sys.argv


def load_credentials():
    cid = secret = None
    try:
        import keyring
        cid = keyring.get_password("AutoSocialPoster", "linkedin_client_id")
        secret = keyring.get_password("AutoSocialPoster", "linkedin_client_secret")
        if cid:
            print("[creds] source: Windows vault")
    except Exception as e:
        print(f"[creds] keyring unavailable: {e}")
    if not cid or not secret:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass
        cid = cid or os.getenv("LINKEDIN_CLIENT_ID", "").strip()
        secret = secret or os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()
        print("[creds] source: .env / environment")
    return (cid or "").strip(), (secret or "").strip()


client_id, client_secret = load_credentials()
print(f"[creds] client_id={client_id!r}")
print(f"[creds] secret_len={len(client_secret)} starts_with={client_secret[:4]!r} ends_with={client_secret[-2:]!r}")
if not client_id or not client_secret:
    sys.exit("No credentials found.")

# Step 1: sanity check credentials with a fake code
r = httpx.post(
    "https://www.linkedin.com/oauth/v2/accessToken",
    data={
        "grant_type": "authorization_code",
        "code": "fake",
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "client_secret": client_secret,
    },
)
print(f"\n[step 1] fake-code check -> {r.status_code} {r.text}")
if "invalid_client" in r.text:
    sys.exit("FAIL: credentials rejected. Wrong ID/secret pair.")
print("[step 1] OK: credentials accepted (error above is about the fake code, expected).")

# Step 2: real flow
state = secrets.token_urlsafe(16)
params = {
    "response_type": "code",
    "client_id": client_id,
    "redirect_uri": REDIRECT_URI,
    "state": state,
    "scope": "openid profile w_member_social",
}
verifier = None
if USE_PKCE:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    params["code_challenge"] = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    params["code_challenge_method"] = "S256"

captured = {}
done = threading.Event()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query)
        captured.update({k: v[0] for k, v in q.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h3>Got it. You can close this tab and check the terminal.</h3>")
        done.set()

    def log_message(self, *a):
        pass


server = HTTPServer(("127.0.0.1", 8000), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()

print(f"\n[step 2] mode: {'PKCE + secret' if USE_PKCE else 'secret only (no PKCE)'}")
print("[step 2] opening browser, approve the LinkedIn prompt...")
webbrowser.open("https://www.linkedin.com/oauth/v2/authorization?" + urlencode(params))

if not done.wait(timeout=180):
    server.shutdown()
    sys.exit("Timed out waiting for callback.")
server.shutdown()

if captured.get("state") != state:
    sys.exit(f"State mismatch: {captured}")
if "code" not in captured:
    sys.exit(f"No code returned: {captured}")

data = {
    "grant_type": "authorization_code",
    "code": captured["code"],
    "redirect_uri": REDIRECT_URI,
    "client_id": client_id,
    "client_secret": client_secret,
}
if verifier:
    data["code_verifier"] = verifier

r = httpx.post("https://www.linkedin.com/oauth/v2/accessToken", data=data)
print(f"\n[step 3] token exchange -> {r.status_code}")
if r.is_success:
    tok = r.json()
    print(f"PASS: got access_token (len {len(tok['access_token'])}), expires_in={tok.get('expires_in')}")
    u = httpx.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {tok['access_token']}"},
    )
    print(f"[step 4] userinfo -> {u.status_code} {u.text[:200]}")
else:
    print(f"FAIL: {r.text}")
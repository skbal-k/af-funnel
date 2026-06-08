"""
Hace el flujo OAuth de Google una sola vez y guarda el token en gas_token.json.
Corré esto primero, luego sync_to_sheets.py funciona solo.

Uso: python3 get_google_token.py
"""
import json
import urllib.request
import urllib.parse
import webbrowser
import http.server
import threading
from pathlib import Path

CREDS_PATH = Path(__file__).parent.parent / "personal-assistant" / "credentials.json"
TOKEN_PATH  = Path(__file__).parent / "gas_token.json"

SCOPES = " ".join([
    "openid",
    "email",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/script.external_request",
])

REDIRECT_URI = "http://localhost:8080"

auth_code = None


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h2>Listo. Podes cerrar esta ventana y volver a la terminal.</h2>")

    def log_message(self, *args):
        pass


def main():
    creds = json.loads(CREDS_PATH.read_text())["installed"]

    auth_url = (
        creds["auth_uri"]
        + "?" + urllib.parse.urlencode({
            "client_id":     creds["client_id"],
            "redirect_uri":  REDIRECT_URI,
            "response_type": "code",
            "scope":         SCOPES,
            "access_type":   "offline",
            "prompt":        "consent",
        })
    )

    server = http.server.HTTPServer(("localhost", 8080), Handler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    print("\n  Abriendo el browser...")
    print("  → Logeate con tu cuenta @salesforce.com")
    print("  → La ventana se cierra sola al terminar\n")
    webbrowser.open(auth_url)
    thread.join()

    if not auth_code:
        print("❌ No se recibió el código de autorización.")
        return

    # Intercambiar code por tokens
    token_payload = urllib.parse.urlencode({
        "code":          auth_code,
        "client_id":     creds["client_id"],
        "client_secret": creds["client_secret"],
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    }).encode()

    req = urllib.request.Request(
        creds["token_uri"], data=token_payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST"
    )
    with urllib.request.urlopen(req) as r:
        tokens = json.loads(r.read().decode())

    TOKEN_PATH.write_text(json.dumps(tokens, indent=2))
    print(f"✓ Token guardado en {TOKEN_PATH}")
    print(f"  Cuenta: {tokens.get('id_token', '?')[:30]}...")


if __name__ == "__main__":
    main()

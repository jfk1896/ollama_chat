#!/usr/bin/env python3
"""Local chat page for the Ollama API. Listens on 127.0.0.1 only."""

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HOST = "127.0.0.1"
PORT = 8080
OLLAMA = os.environ.get("OLLAMA_HOST_URL", "http://127.0.0.1:11434").rstrip("/")
ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            body = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith("/api/"):
            self._proxy()
            return
        self.send_error(404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/"):
            self._proxy()
            return
        self.send_error(404)

    def _proxy(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        payload = self.rfile.read(length) if length else None
        req = Request(OLLAMA + self.path, data=payload, method=self.command)
        if payload is not None:
            req.add_header("Content-Type", self.headers.get("Content-Type", "application/json"))
        try:
            resp = urlopen(req, timeout=600)
        except HTTPError as exc:
            body = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "text/plain"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        except URLError as exc:
            message = ("Ollama is not answering on %s (%s)." % (OLLAMA, exc.reason)).encode()
            self.send_response(502)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)
            return

        self.send_response(resp.status)
        content_type = resp.headers.get("Content-Type", "application/json")
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        try:
            while True:
                chunk = resp.read(2048)
                if not chunk:
                    break
                self.wfile.write(b"%X\r\n" % len(chunk))
                self.wfile.write(chunk)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
        finally:
            resp.close()
        try:
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print("Ollama chat at http://%s:%s/" % (HOST, PORT), flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()

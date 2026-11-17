#!/usr/bin/env python3
"""rx1print - tiny HTTP print API for a DNP DS-RX1HS on CUPS (Orange Pi / Raspberry Pi).

Endpoints
  GET  /health                      -> printer status (JSON)
  POST /print?layout=4x6&copies=1   -> body = raw image bytes (jpeg/png)
       layout: 4x6   (default) one photo fills a 4x6" print
               strip two 2x6" strips side by side on one 4x6" print
               (cut in half after printing)

Config (environment variables)
  RX1_PRINTER   CUPS queue name            (default DNP-RX1HS)
  RX1_BIND      listen address             (default 0.0.0.0)
  RX1_PORT      listen port                (default 8080)
  RX1_TOKEN     if set, clients must send  "Authorization: Bearer <token>"
  RX1_MEDIA     CUPS media option, e.g. w288h432 (default: printer default)
  RX1_MAX_MB    max upload size in MB      (default 25)
  RX1_MAX_COPIES max copies per request    (default 5)

Only needs Python 3.8+, Pillow and the CUPS `lp`/`lpstat` commands.
"""
import hmac
import io
import json
import os
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageOps

PRINTER = os.environ.get("RX1_PRINTER", "DNP-RX1HS")
BIND = os.environ.get("RX1_BIND", "0.0.0.0")
PORT = int(os.environ.get("RX1_PORT", "8080"))
TOKEN = os.environ.get("RX1_TOKEN", "")
MEDIA = os.environ.get("RX1_MEDIA", "")
MAX_BYTES = int(float(os.environ.get("RX1_MAX_MB", "25")) * 1024 * 1024)
MAX_COPIES = int(os.environ.get("RX1_MAX_COPIES", "5"))

DPI = 300
W, H = 4 * DPI, 6 * DPI  # 4x6 portrait canvas


def compose(img: Image.Image, layout: str) -> Image.Image:
    """Return a 1200x1800 RGB canvas ready to print."""
    img = ImageOps.exif_transpose(img).convert("RGB")
    if layout == "4x6":
        # photo may be landscape or portrait; rotate so it fills a portrait 4x6
        if img.width > img.height:
            img = img.rotate(90, expand=True)
        return ImageOps.fit(img, (W, H), Image.LANCZOS)
    if layout == "strip":
        strip = ImageOps.fit(img, (W // 2, H), Image.LANCZOS)  # 2x6 each
        canvas = Image.new("RGB", (W, H), "white")
        canvas.paste(strip, (0, 0))
        canvas.paste(strip, (W // 2, 0))
        return canvas
    raise ValueError("layout must be '4x6' or 'strip'")


def lp_print(path: str, copies: int) -> str:
    cmd = ["lp", "-d", PRINTER, "-n", str(copies), "-o", "fit-to-page"]
    if MEDIA:
        cmd += ["-o", f"media={MEDIA}"]
    cmd.append(path)
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "lp failed")
    return out.stdout.strip()  # "request id is DNP-RX1HS-12 (1 file(s))"


def printer_status() -> dict:
    out = subprocess.run(["lpstat", "-p", PRINTER], capture_output=True, text=True, timeout=10)
    text = (out.stdout or out.stderr).strip()
    return {"printer": PRINTER, "ok": out.returncode == 0, "status": text}


class Handler(BaseHTTPRequestHandler):
    server_version = "rx1print/1.0"

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        if not TOKEN:
            return True
        got = self.headers.get("Authorization", "")
        return hmac.compare_digest(got, f"Bearer {TOKEN}")

    def do_GET(self):
        if urlparse(self.path).path == "/health":
            return self._send(200, printer_status())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        if url.path != "/print":
            return self._send(404, {"error": "not found"})
        if not self._authorized():
            return self._send(401, {"error": "unauthorized"})

        q = parse_qs(url.query)
        layout = q.get("layout", ["4x6"])[0]
        try:
            copies = int(q.get("copies", ["1"])[0])
        except ValueError:
            return self._send(400, {"error": "copies must be a number"})
        if not 1 <= copies <= MAX_COPIES:
            return self._send(400, {"error": f"copies must be 1-{MAX_COPIES}"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return self._send(411, {"error": "Content-Length required"})
        if length > MAX_BYTES:
            return self._send(413, {"error": "image too large"})

        data = self.rfile.read(length)
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
            canvas = compose(img, layout)
        except ValueError as e:
            return self._send(400, {"error": str(e)})
        except Exception:
            return self._send(415, {"error": "not a valid image"})

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "print.png")
            canvas.save(path, dpi=(DPI, DPI))
            try:
                job = lp_print(path, copies)
            except Exception as e:
                return self._send(502, {"error": str(e)})
        self._send(200, {"ok": True, "job": job, "layout": layout, "copies": copies})

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


if __name__ == "__main__":
    print(f"rx1print on {BIND}:{PORT} -> CUPS queue '{PRINTER}'", flush=True)
    ThreadingHTTPServer((BIND, PORT), Handler).serve_forever()

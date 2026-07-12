#!/usr/bin/env python3
"""
ICX Show-Tech Analyzer - static file server + Azure OpenAI backend proxy.

Why a backend proxy?
--------------------
The single-page app can call Azure OpenAI directly from the browser, but that
(1) exposes your API key in client-side code / sessionStorage, and
(2) is blocked by CORS because Azure OpenAI does not send CORS headers.

This tiny server (Python standard library only - no pip installs) solves both:
it holds the Azure OpenAI key server-side and exposes a same-origin API that
the page calls instead.

Endpoints
---------
    GET  /                 -> serves ICX_ShowTech_Analyzer_v3_0.html
    GET  /api/ai/status    -> {"configured": bool, "deployment": str, "apiVersion": str}
                              (never returns the key)
    POST /api/ai/chat      -> forwards {messages, max_tokens, temperature} to
                              Azure OpenAI Chat Completions and returns the
                              Azure JSON response verbatim.

Configuration (environment variables)
--------------------------------------
    AZURE_OPENAI_ENDPOINT      e.g. https://my-resource.openai.azure.com
    AZURE_OPENAI_API_KEY       Azure OpenAI key (KEY 1 or KEY 2)
    AZURE_OPENAI_DEPLOYMENT    model deployment name, e.g. gpt-4o
    AZURE_OPENAI_API_VERSION   default: 2024-12-01-preview
    HOST                       default: 0.0.0.0
    PORT                       default: 8000

Run
---
    export AZURE_OPENAI_ENDPOINT="https://my-resource.openai.azure.com"
    export AZURE_OPENAI_API_KEY="<key>"
    export AZURE_OPENAI_DEPLOYMENT="gpt-4o"
    python3 server.py
    # open http://localhost:8000/
"""
import json
import os
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOC = "ICX_ShowTech_Analyzer_v3_0.html"


def get_config():
    return {
        "endpoint": (os.environ.get("AZURE_OPENAI_ENDPOINT") or "").rstrip("/"),
        "key": os.environ.get("AZURE_OPENAI_API_KEY") or "",
        "deployment": os.environ.get("AZURE_OPENAI_DEPLOYMENT") or "",
        "version": os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-12-01-preview",
    }


def is_configured(cfg):
    return bool(cfg["endpoint"] and cfg["key"] and cfg["deployment"])


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # ---- helpers ----
    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    # ---- routes ----
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/ai/status":
            cfg = get_config()
            return self._send_json(200, {
                "configured": is_configured(cfg),
                "deployment": cfg["deployment"],
                "apiVersion": cfg["version"],
            })
        if path in ("/", ""):
            self.path = "/" + DEFAULT_DOC
        return super().do_GET()

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/ai/chat":
            return self._send_json(404, {"error": "not found"})

        cfg = get_config()
        if not is_configured(cfg):
            return self._send_json(503, {
                "error": "Azure OpenAI is not configured on the server. Set "
                         "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and "
                         "AZURE_OPENAI_DEPLOYMENT."
            })

        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception as exc:  # noqa: BLE001
            return self._send_json(400, {"error": "invalid JSON body: %s" % exc})

        # Only forward a fixed, safe set of fields.
        upstream_body = {
            "messages": payload.get("messages", []),
            "max_tokens": payload.get("max_tokens", 1200),
            "temperature": payload.get("temperature", 0.3),
        }

        url = "%s/openai/deployments/%s/chat/completions?api-version=%s" % (
            cfg["endpoint"], cfg["deployment"], cfg["version"],
        )
        req = urllib.request.Request(
            url,
            data=json.dumps(upstream_body).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("api-key", cfg["key"])

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                try:
                    parsed = json.loads(data)
                except Exception:  # noqa: BLE001
                    parsed = {"raw": data.decode("utf-8", "replace")}
                return self._send_json(getattr(resp, "status", 200), parsed)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail)
            except Exception:  # noqa: BLE001
                pass
            return self._send_json(exc.code, {
                "error": "Azure OpenAI returned an error",
                "status": exc.code,
                "detail": detail,
            })
        except Exception as exc:  # noqa: BLE001
            return self._send_json(502, {"error": "upstream request failed: %s" % exc})


def main():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    cfg = get_config()
    print("ICX Show-Tech Analyzer server: http://%s:%d/" % (host, port))
    print("  Serving:            %s" % os.path.join(ROOT, DEFAULT_DOC))
    print("  Azure OpenAI ready: %s (deployment=%s, api-version=%s)" % (
        is_configured(cfg), cfg["deployment"] or "-", cfg["version"],
    ))
    if not is_configured(cfg):
        print("  NOTE: set AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY / "
              "AZURE_OPENAI_DEPLOYMENT to enable AI answers.")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import base64
import json
import logging
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Tuple


TARGET_BASE = "https://api.scan.hearables3d.com.au"
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def headers_to_dict(headers) -> Dict[str, str]:
    return {key: value for key, value in headers.items()}


def encode_body(body: bytes) -> Dict[str, str]:
    try:
        return {"text": body.decode("utf-8")}
    except UnicodeDecodeError:
        return {"base64": base64.b64encode(body).decode("ascii")}


def response_from_error(exc: urllib.error.HTTPError) -> Tuple[int, Dict[str, str], bytes]:
    body = exc.read()
    return exc.code, headers_to_dict(exc.headers), body


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "HearablesProxy/1.0"

    def do_GET(self):
        self.proxy_request()

    def do_POST(self):
        self.proxy_request()

    def do_PUT(self):
        self.proxy_request()

    def do_PATCH(self):
        self.proxy_request()

    def do_DELETE(self):
        self.proxy_request()

    def do_HEAD(self):
        self.proxy_request()

    def do_OPTIONS(self):
        self.proxy_request()

    def proxy_request(self):
        started_at = time.time()
        request_body = self.read_request_body()
        target_url = f"{self.server.target_base}{self.path}"
        request_headers = self.forward_headers()

        request = urllib.request.Request(
            target_url,
            data=request_body if self.command not in {"GET", "HEAD"} else None,
            headers=request_headers,
            method=self.command,
        )

        try:
            with urllib.request.urlopen(request, timeout=self.server.timeout_seconds) as upstream:
                status = upstream.status
                response_headers = headers_to_dict(upstream.headers)
                response_body = upstream.read()
        except urllib.error.HTTPError as exc:
            status, response_headers, response_body = response_from_error(exc)
        except Exception as exc:
            response_body = str(exc).encode("utf-8")
            response_headers = {"content-type": "text/plain; charset=utf-8"}
            status = 502

        self.send_response(status)
        for key, value in response_headers.items():
            if key.lower() not in HOP_BY_HOP_HEADERS:
                self.send_header(key, value)
        self.end_headers()

        if self.command != "HEAD":
            self.wfile.write(response_body)

        self.log_exchange(
            started_at=started_at,
            target_url=target_url,
            request_body=request_body,
            response_status=status,
            response_headers=response_headers,
            response_body=response_body,
        )

    def read_request_body(self) -> bytes:
        length = int(self.headers.get("content-length", "0") or "0")
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def forward_headers(self) -> Dict[str, str]:
        headers = {}
        for key, value in self.headers.items():
            lower_key = key.lower()
            if lower_key in HOP_BY_HOP_HEADERS or lower_key in {"host", "content-length"}:
                continue
            headers[key] = value
        headers["Host"] = urllib.parse.urlparse(self.server.target_base).netloc
        return headers

    def log_exchange(
        self,
        started_at: float,
        target_url: str,
        request_body: bytes,
        response_status: int,
        response_headers: Dict[str, str],
        response_body: bytes,
    ):
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_at)),
            "duration_ms": round((time.time() - started_at) * 1000, 2),
            "client": self.client_address[0],
            "method": self.command,
            "path": self.path,
            "target_url": target_url,
            "request": {
                "headers": headers_to_dict(self.headers),
                "body": encode_body(request_body),
            },
            "response": {
                "status": response_status,
                "headers": response_headers,
                "body": encode_body(response_body),
            },
        }
        self.server.log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.server.log_file.flush()

    def log_message(self, fmt, *args):
        logging.info("%s - %s", self.address_string(), fmt % args)


class ProxyServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler, target_base, timeout_seconds, log_file):
        super().__init__(server_address, handler)
        self.target_base = target_base.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.log_file = log_file


def parse_args():
    parser = argparse.ArgumentParser(description="HTTP logging proxy for api.scan.hearables3d.com.au")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    parser.add_argument("--log", default="proxy-log.jsonl", help="JSONL file for request/response logs")
    parser.add_argument("--target", default=TARGET_BASE)
    parser.add_argument("--timeout", default=60, type=float)
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    with open(args.log, "a", encoding="utf-8") as log_file:
        server = ProxyServer((args.host, args.port), ProxyHandler, args.target, args.timeout, log_file)

        logging.info("Serving HTTP proxy on http://%s:%s", args.host, args.port)
        logging.info("Forwarding requests to %s", server.target_base)
        logging.info("Writing JSONL logs to %s", args.log)

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down")
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

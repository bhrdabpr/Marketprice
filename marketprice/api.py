"""Authenticated local JSON pricing API; no marketplace writes or network fetches."""

import hmac
import json
import os
from wsgiref.simple_server import make_server

from .flexible import calculate_catalog
from .io import MAX_BYTES, json_default


def create_app(token: str):
    if len(token) < 24:
        raise ValueError("MARKETPRICE_API_TOKEN must contain at least 24 characters")

    def app(environ, start_response):
        def respond(status, payload):
            body = json.dumps(payload, default=json_default, ensure_ascii=False).encode()
            start_response(
                status,
                [
                    ("Content-Type", "application/json; charset=utf-8"),
                    ("Content-Length", str(len(body))),
                    ("Cache-Control", "no-store"),
                ],
            )
            return [body]

        supplied = environ.get("HTTP_AUTHORIZATION", "")
        if not hmac.compare_digest(supplied.encode(), ("Bearer " + token).encode()):
            return respond("401 Unauthorized", {"error": "Bearer token required"})
        if environ.get("PATH_INFO") != "/v1/calculate":
            return respond("404 Not Found", {"error": "Unknown endpoint"})
        if environ.get("REQUEST_METHOD") != "POST":
            return respond("405 Method Not Allowed", {"error": "Use POST"})
        try:
            size = int(environ.get("CONTENT_LENGTH", "0"))
            if not 0 < size <= MAX_BYTES:
                return respond("413 Payload Too Large", {"error": "Body must be 1 byte to 25 MiB"})
            payload = json.loads(
                environ["wsgi.input"].read(size),
                parse_float=str,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")),
            )
            if not isinstance(payload, dict) or set(payload) - {"products", "settings"}:
                raise ValueError("Expected products and settings")
            settings = payload.get("settings", {})
            if not isinstance(settings, dict) or set(settings) - {
                "currency",
                "target_margin",
                "marketplace",
                "locale",
            }:
                raise ValueError("Unknown settings")
            if not isinstance(payload.get("products"), list):
                raise TypeError("products must be an array")
            if not all(isinstance(v, str) for v in settings.values()):
                raise ValueError("Settings must be strings")
            if not {"currency", "target_margin"} <= settings.keys():
                raise ValueError("currency and target_margin settings are required")
            result = calculate_catalog(payload["products"], **settings)
            return respond("200 OK", result)
        except (ValueError, TypeError, KeyError, RecursionError):
            return respond(
                "400 Bad Request", {"error": "Invalid request: check products, column mapping and settings"}
            )
        except Exception:  # noqa: BLE001 - never expose inputs or internals
            return respond("500 Internal Server Error", {"error": "Calculation failed"})

    return app


def main():
    app = create_app(os.environ.get("MARKETPRICE_API_TOKEN", ""))
    port = int(os.environ.get("MARKETPRICE_API_PORT", "8502"))
    with make_server("127.0.0.1", port, app) as server:
        print(f"MarketPrice local API listening on http://127.0.0.1:{port}/v1/calculate")
        server.serve_forever()


if __name__ == "__main__":
    main()

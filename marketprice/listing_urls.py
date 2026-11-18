"""Read public product copy for the two supported Amazon storefronts."""

import http.client
import re
import ssl
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

import certifi

MARKETS = {"amazon.com", "amazon.ae"}
MAX_BYTES = 8 * 1024 * 1024
MAX_LINKS = 20
PRODUCT_PATH = re.compile(r"/(?:-/(?:en|ar)/)?(?:[^/]+/)?(?:dp|gp/product)/([A-Za-z0-9]{10})(?:/.*)?")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def product_url(raw, market):
    if market not in MARKETS:
        raise ValueError("Unsupported marketplace.")
    parts = urlsplit(raw.strip())
    if parts.scheme != "https" or parts.netloc.lower() not in {market, "www." + market}:
        raise ValueError("Use an HTTPS product link from the selected Amazon store.")
    match = PRODUCT_PATH.fullmatch(parts.path)
    if not match:
        raise ValueError("Use the full Amazon link containing /dp/ASIN or /gp/product/ASIN.")
    asin = match[1].upper()
    return f"https://www.{market}/dp/{asin}", asin


class ProductText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack: list[tuple[str, str]] = []
        self.parts: dict[str, list[str]] = {}
        self.bullets = 0
        self.asin = ""
        self.canonical = ""

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        ident = props.get("id")
        scope = self.stack[-1][1] if self.stack else ""
        if tag == "link" and props.get("rel") == "canonical":
            self.canonical = props.get("href") or ""
        if tag == "input" and ident == "ASIN":
            self.asin = props.get("value") or ""
        if scope == "skip" or tag in {"style", "script", "noscript", "template"} or "hidden" in props:
            scope = "skip"
        elif ident == "productTitle":
            scope = "title"
        elif ident == "feature-bullets":
            scope = "bullets"
        elif ident == "productDescription":
            scope = "description"
        elif scope == "bullets" and tag == "li":
            self.bullets += 1
            scope = f"bullet_{self.bullets}" if self.bullets <= 10 else "skip"
        if scope in self.parts and tag in {"br", "p", "div"}:
            self.parts[scope].append(" ")
        if tag not in VOID:
            if len(self.stack) >= 256:
                raise ValueError("HTML nesting limit exceeded.")
            self.stack.append((tag, scope))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        scope = self.stack[-1][1] if self.stack else ""
        if scope in {"title", "description"} or scope.startswith("bullet_"):
            self.parts.setdefault(scope, []).append(data)


def parse_page(body, market, asin, *, saved=False):
    if len(body) > MAX_BYTES:
        raise ValueError("Page exceeds the 8 MiB limit.")
    parser = ProductText()
    try:
        parser.feed(body.decode("utf-8-sig", errors="replace"))
        parser.close()
    except (ValueError, AssertionError) as exc:
        raise ValueError("Could not read this HTML page.") from exc
    row = {"sku": asin}
    for key, fragments in parser.parts.items():
        value = " ".join("".join(fragments).split())
        if value:
            if len(value) > 32767:
                raise ValueError("Listing field is too long for an Excel cell.")
            row[key] = value
    if "title" not in row:
        raise ValueError("Product title unavailable. Amazon may require a browser or use a different layout.")
    if parser.asin and parser.asin.upper() != asin:
        raise ValueError("Page ASIN differs from the requested product.")
    if parser.canonical:
        canonical_asin = product_url(parser.canonical, market)[1]
        if canonical_asin != asin:
            raise ValueError("Canonical product differs from the requested product.")
    if saved and not parser.canonical:
        raise ValueError("Saved HTML must include a matching Amazon canonical product link.")
    return row


def fetch_page(market, asin):
    # Only a fixed storefront and a validated ASIN can reach the network.
    if market not in MARKETS or not re.fullmatch(r"[A-Z0-9]{10}", asin):
        raise ValueError("Invalid product address.")
    context = ssl.create_default_context()
    context.load_verify_locations(certifi.where())
    connection = http.client.HTTPSConnection("www." + market, timeout=8, context=context)
    try:
        connection.request("GET", "/dp/" + asin, headers={"Accept": "text/html", "Accept-Language": "en",
                                                        "User-Agent": "MarketPrice/1.0 (product listing reader)"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f"Amazon returned HTTP {response.status}. Use a saved HTML page.")
        if response.headers.get_content_type() != "text/html":
            raise ValueError("Amazon returned a non-HTML response.")
        return response.read(MAX_BYTES + 1)
    except (OSError, http.client.HTTPException) as exc:
        raise ValueError("The Amazon page could not be reached. Use a saved HTML page.") from exc
    finally:
        connection.close()


def read_products(lines, market, saved_html=None):
    if not 1 <= len(lines) <= MAX_LINKS or (saved_html is not None and len(lines) != 1):
        raise ValueError("Enter 1 to 20 links, or one link for a saved page.")
    rows, sources = [], []
    seen = set()
    for line, raw in enumerate(lines, 1):
        source = {"line": line, "marketplace": market, "source_url": "", "asin": "",
                  "source_type": "saved_html" if saved_html is not None else "public_url",
                  "read_at_utc": datetime.now(UTC).isoformat(timespec="seconds")}
        try:
            url, asin = product_url(raw, market)
            source.update(source_url=url, asin=asin)
            if asin in seen:
                source["status"] = "Duplicate link"
            else:
                seen.add(asin)
                body = saved_html if saved_html is not None else fetch_page(market, asin)
                row = parse_page(body, market, asin, saved=saved_html is not None)
                rows.append(row)
                source.update(status="Read", fields=", ".join(k for k in row if k != "sku"))
        except ValueError as exc:
            source["status"] = str(exc)
        sources.append(source)
    return rows, sources

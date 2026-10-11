"""A fake Shopify-style shop (made-up brands) for tests, the setup check and the README screenshot.

  python tests/fake_shop.py --port 8765

Serves /robots.txt, /products.json (paged), /collections/sale/products.json, /products/<handle>.json,
/sitemap.xml and JSON-LD product pages under /p/<handle>.
"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

LETTERS = ["S", "M", "L", "XL", "XXL"]


def _p(pid, handle, title, vendor, ptype, price, was, sizes, sold_out=(), colour=None):
    variants = []
    for i, s in enumerate(sizes):
        variants.append({"id": pid * 100 + i, "option1": s, "option2": colour, "price": f"{price:.2f}",
                         "compare_at_price": f"{was:.2f}" if was else None, "available": s not in sold_out})
    opts = [{"name": "Size", "values": list(sizes)}] + ([{"name": "Colour", "values": [colour]}] if colour else [])
    return {"id": pid, "handle": handle, "title": title, "vendor": vendor, "product_type": ptype, "tags": ["sale"] if was else [],
            "options": opts, "variants": variants, "images": [{"src": f"https://img.invalid/{handle}.jpg"}]}


PRODUCTS = [
    _p(1, "loopback-hoodie-navy", "Loopback Hoodie - Navy", "Northfold", "Hoodies", 48, 85, LETTERS, sold_out=("M",)),
    _p(2, "loopback-hoodie-grey", "Loopback Hoodie - Grey", "Northfold", "Hoodies", 52, 85, LETTERS),
    _p(3, "boxy-pocket-tee-olive", "Boxy Pocket Tee - Olive", "Harbour & Pine", "T-Shirts", 18, 32, LETTERS),
    _p(4, "relaxed-oxford-shirt", "Relaxed Oxford Shirt - Blue", "Ashgrove", "Shirts", 59, 95, LETTERS),
    _p(5, "straight-selvedge-jeans", "Straight Selvedge Jeans - Indigo", "Northfold", "Jeans", 89, 140,
       ["30R", "32R", "32L", "34R", "36R"]),
    _p(6, "skinny-stretch-jeans", "Skinny Stretch Jeans - Black", "Ashgrove", "Jeans", 25, 60, ["30R", "32R", "34R"]),
    _p(7, "pleated-wide-trousers", "Pleated Wide Trousers - Stone", "Harbour & Pine", "Trousers", 38, 70, ["W30 L32", "W32 L32", "W34 L32"]),
    _p(8, "court-trainer-white", "Court Trainer - White", "Harbour & Pine", "Trainers", 74, 120, ["7", "8", "9", "9.5", "10", "11"]),
    _p(9, "trail-runner-olive", "Trail Runner - Olive", "Ashgrove", "Shoes", 115, 180, ["42", "43", "44", "44.5", "45", "46"]),
    _p(10, "harrington-jacket-navy", "Harrington Jacket - Navy", "Ashgrove", "Jackets", 120, 210, LETTERS),
    _p(11, "kids-logo-tee", "Kids Logo Tee", "Northfold", "Kids", 8, 14, ["7-8Y", "9-10Y"]),
    _p(12, "track-pant-black", "Track Pant - Black", "Northfold", "Joggers", 30, 55, LETTERS),
    _p(13, "heavy-tee-pink", "Heavyweight Tee - Pink", "Harbour & Pine", "T-Shirts", 15, 30, LETTERS),
    _p(14, "chunky-knit-jumper", "Chunky Knit Jumper - Green", "Ashgrove", "Knitwear", 140, 220, LETTERS, sold_out=("M", "L")),
]


def jsonld_page(p: dict) -> str:
    offers = [{"@type": "Offer", "size": v["option1"], "price": v["price"], "priceCurrency": "GBP",
               "availability": "https://schema.org/" + ("InStock" if v["available"] else "OutOfStock")} for v in p["variants"]]
    ld = {"@context": "https://schema.org", "@type": "Product", "name": p["title"], "brand": {"@type": "Brand", "name": p["vendor"]},
          "category": p["product_type"], "image": p["images"][0]["src"], "offers": offers}
    return f"<html><head><script type=\"application/ld+json\">{json.dumps(ld)}</script></head><body>{p['title']}</body></html>"


class Handler(BaseHTTPRequestHandler):
    page_size = 250

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        base = f"http://{self.headers.get('Host')}"
        if u.path == "/robots.txt":
            return self._send(200, "User-agent: *\nDisallow: /private\n", "text/plain")
        if u.path in ("/products.json", "/collections/sale/products.json"):
            items = PRODUCTS if u.path == "/products.json" else [p for p in PRODUCTS if "sale" in p["tags"]]
            page, limit = int(q.get("page", ["1"])[0]), min(int(q.get("limit", ["30"])[0]), self.page_size)
            return self._send(200, json.dumps({"products": items[(page - 1) * limit: page * limit]}))
        if u.path.startswith("/products/") and u.path.endswith(".json"):
            h = u.path[len("/products/"):-5]
            p = next((x for x in PRODUCTS if x["handle"] == h), None)
            return self._send(200, json.dumps({"product": p})) if p else self._send(404, "{}")
        if u.path == "/sitemap.xml":
            locs = "".join(f"<url><loc>{base}/p/{p['handle']}</loc></url>" for p in PRODUCTS)
            return self._send(200, f"<?xml version='1.0'?><urlset>{locs}</urlset>", "application/xml")
        if u.path.startswith("/p/"):
            p = next((x for x in PRODUCTS if x["handle"] == u.path[3:]), None)
            return self._send(200, jsonld_page(p), "text/html") if p else self._send(404, "nope", "text/plain")
        if u.path.startswith("/private"):
            return self._send(200, "secret", "text/plain")
        return self._send(404, "not here", "text/plain")


def start(port: int = 0):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"fake shop on http://127.0.0.1:{a.port}", flush=True)
    srv.serve_forever()

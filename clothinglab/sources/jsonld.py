"""Any shop that publishes a sitemap and schema.org Product JSON-LD on its product pages.

Per-size stock only exists when the shop lists one Offer per size (with `size`, `name` or `sku` carrying the size
and `availability` saying InStock). Plenty of high-street shops don't: they publish one Offer for the product and
load size stock later with JavaScript. Those items come back with sizes_available = None ("size unknown"), and are
never presented as in your size.
"""
from __future__ import annotations

import json
import re
from html import unescape

from .. import catalog
from ..store import now_iso

LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
LD = re.compile(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", re.I | re.S)


def _products(node):
    if isinstance(node, list):
        for n in node:
            yield from _products(n)
    elif isinstance(node, dict):
        t = node.get("@type")
        if t == "Product" or (isinstance(t, list) and "Product" in t):
            yield node
        if t == "ProductGroup":
            for v in node.get("hasVariant") or []:
                yield {**v, "_group": node}
        for k in ("@graph", "mainEntity"):
            if k in node:
                yield from _products(node[k])


def _offers(p):
    o = p.get("offers") or []
    if isinstance(o, dict):
        o = o.get("offers") or [o]
    return [x for x in o if isinstance(x, dict)]


def _num(x):
    try:
        return round(float(str(x).replace(",", "")), 2)
    except (TypeError, ValueError):
        return None


def parse_page(html: str, url: str, src: dict) -> dict | None:
    prods = []
    for block in LD.findall(html):
        try:
            prods.extend(_products(json.loads(unescape(block).strip())))
        except ValueError:
            continue
    if not prods:
        return None
    group = prods[0].get("_group") or prods[0]
    title = group.get("name") or prods[0].get("name") or ""
    cat = catalog.category(title, str(group.get("category", "")))
    if not cat:
        return None
    listed, available, prices = [], [], []
    per_size = False
    for p in prods:
        for off in _offers(p):
            size = p.get("size") or off.get("size") or None
            if not size and len(prods) == 1 and len(_offers(p)) > 1:
                size = off.get("name") or off.get("sku")
            price = _num(off.get("price") or (off.get("priceSpecification") or {}).get("price"))
            stock = "instock" in str(off.get("availability", "")).lower()
            if price is not None and stock:
                prices.append(price)
            if size:
                per_size = True
                size = str(size).strip()
                if size not in listed:
                    listed.append(size)
                if stock and size not in available:
                    available.append(size)
    price = min(prices) if prices else None
    brand = group.get("brand")
    brand = brand.get("name") if isinstance(brand, dict) else brand
    image = group.get("image")
    image = image[0] if isinstance(image, list) and image else image
    return {
        "id": f"{src['name']}:{url.rstrip('/').rsplit('/', 1)[-1]}",
        "source": src["name"], "title": title, "brand": brand or src["name"], "url": url,
        "image": image if isinstance(image, str) else None, "category": cat,
        "garment": catalog.garment(title, str(group.get("category", ""))),
        "price": price, "was": None, "currency": src.get("currency", "GBP"), "discount": 0.0,
        "sizes_listed": listed if per_size else None,
        "sizes_available": available if per_size else None,
        "size_scale": src.get("shoe_scale"), "colour": f"{title} {group.get('color', '')}",
        "product_type": str(group.get("category", "")), "tags": [], "seen_at": now_iso(),
    }


def fetch(fetcher, src: dict) -> list[dict]:
    pattern = re.compile(src.get("product_url_pattern", r"/products?/"))
    urls = [u for u in LOC.findall(fetcher.text(src["sitemap"])) if pattern.search(u)]
    out = []
    for u in urls[: int(src.get("max_pages", 40))]:
        try:
            it = parse_page(fetcher.text(u), u, src)
        except Exception:      # one bad page never sinks the source
            continue
        if it:
            out.append(it)
    return out

"""Any Shopify store, via the public /products.json (or /collections/<handle>/products.json for a sale page).

Each variant carries its option values and an `available` flag, which is what makes "in stock IN YOUR SIZE"
possible at all. The size is whichever option is named Size (or looks like sizes), and it can be glued to a
colour ("46 2/3 / Cream / Blue"), which sizes.py copes with.
"""
from __future__ import annotations

import re

from .. import catalog, sizes
from ..store import now_iso

SIZE_OPT = re.compile(r"\b(size|taille|größe|grosse|maat|talla|waist|shoe)\b", re.I)
RANGE_OPT = re.compile(r"\b(fit|length|range)\b", re.I)
LOOKS_LIKE_SIZE = re.compile(r"^\s*(?:xxs|xs|s|m|l|xl|xxl|[2-4]xl|\d{1,2}(?:[.,]\d)?|w?\d{2}(?:\s*[x/l]\s*\d{2})?)\b", re.I)


def _size_index(product: dict) -> int | None:
    opts = product.get("options") or []
    for i, o in enumerate(opts):
        if SIZE_OPT.search(str(o.get("name", ""))):
            return i
    for i, o in enumerate(opts):
        vals = o.get("values") or []
        if vals and sum(bool(LOOKS_LIKE_SIZE.match(str(v))) for v in vals) >= max(1, len(vals) // 2):
            return i
    return None


def _num(x):
    try:
        return round(float(x), 2) if x not in (None, "") else None
    except (TypeError, ValueError):
        return None


def item_from_product(p: dict, base: str, src: dict) -> dict | None:
    title = p.get("title") or ""
    cat = catalog.category(title, p.get("product_type", ""), " ".join(p.get("tags") or []) if isinstance(p.get("tags"), list) else str(p.get("tags") or ""))
    if not cat:
        return None
    idx = _size_index(p)
    variants = p.get("variants") or []
    if not variants:
        return None
    key = f"option{idx + 1}" if idx is not None else None
    # Petite/Tall/Maternity often live in their own option ("Length: Petite"); fold them into the size label
    # ("10 Petite") so size matching can apply the person's ranges.
    rkey = next((f"option{i + 1}" for i, o in enumerate(p.get("options") or [])
                 if i != idx and RANGE_OPT.search(str(o.get("name", "")))), None)
    listed, available = [], []
    for v in variants:
        lab = str(v.get(key) or "").strip() if key else ""
        rng = sizes.label_range(str(v.get(rkey) or "")) if rkey else None
        if lab and rng:
            lab = f"{lab} {rng.title()}"
        if lab and lab not in listed:
            listed.append(lab)
        if lab and v.get("available") and lab not in available:
            available.append(lab)
    in_stock = [v for v in variants if v.get("available")] or variants
    price = min((_num(v.get("price")) for v in in_stock if _num(v.get("price")) is not None), default=None)
    was = max((_num(v.get("compare_at_price")) for v in in_stock if _num(v.get("compare_at_price"))), default=None)
    if was is not None and price is not None and was <= price:
        was = None
    images = p.get("images") or []
    colour = " ".join(str(o.get("values")) for o in (p.get("options") or []) if re.search(r"colou?r", str(o.get("name", "")), re.I))
    return {
        "id": f"{src['name']}:{p.get('handle')}",
        "source": src["name"],
        "title": title,
        "brand": p.get("vendor") or src.get("brand") or src["name"],
        "url": f"{base}/products/{p.get('handle')}",
        "image": images[0].get("src") if images and isinstance(images[0], dict) else None,
        "category": cat,
        "department": catalog.department(title, p.get("product_type", ""), " ".join(p.get("tags") or []) if isinstance(p.get("tags"), list) else str(p.get("tags") or ""), src.get("department")),
        "range": sizes.label_range(title),
        "garment": catalog.garment(title, p.get("product_type", "")),
        "price": price,
        "was": was,
        "currency": src.get("currency", "GBP"),
        "discount": round(1 - price / was, 3) if was and price else 0.0,
        "sizes_listed": listed,
        "sizes_available": available,
        "size_scale": src.get("shoe_scale"),
        "colour": f"{title} {colour}",
        "product_type": p.get("product_type", ""),
        "tags": p.get("tags") if isinstance(p.get("tags"), list) else [t.strip() for t in str(p.get("tags") or "").split(",") if t.strip()],
        "seen_at": now_iso(),
    }


def fetch(fetcher, src: dict) -> list[dict]:
    base = src["url"].rstrip("/")
    path = f"/collections/{src['collection']}/products.json" if src.get("collection") else "/products.json"
    max_pages = int(src.get("max_pages", 4))
    out = []
    for page in range(1, max_pages + 1):
        data = fetcher.json(f"{base}{path}?limit=250&page={page}")
        products = data.get("products") or []
        for p in products:
            it = item_from_product(p, base, src)
            if it:
                out.append(it)
        if len(products) < 250:
            break
    return out

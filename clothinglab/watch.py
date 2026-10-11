"""Watchlist: things you'd buy at the right price. Checks the product's own public data (Shopify `<url>.json`,
or JSON-LD on the page), never a guess, and reports a drop only when the price really moved.
"""
from __future__ import annotations

from urllib.parse import urlparse

from . import sizes
from .fetch import FetchError
from .sources import jsonld, shopify
from .store import data_dir, load_json, now_iso, save_json


def _path():
    return data_dir() / "watch.json"


def load() -> list[dict]:
    return load_json(_path(), [])


def add(url: str, target: float | None = None, note: str = "") -> dict:
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.netloc:
        raise ValueError("watch needs a full http(s) product URL")
    rows = load()
    row = next((r for r in rows if r["url"] == url), None)
    if row is None:
        row = {"url": url, "added": now_iso(), "price": None, "history": []}
        rows.append(row)
    row.update(target=target, note=note)
    save_json(_path(), rows)
    return row


def remove(url: str) -> bool:
    rows = load()
    keep = [r for r in rows if r["url"] != url]
    save_json(_path(), keep)
    return len(keep) != len(rows)


def _read(fetcher, url: str) -> dict | None:
    src = {"name": urlparse(url).netloc, "currency": "GBP"}
    if "/products/" in url:
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        try:
            p = fetcher.json(url.split("?")[0].rstrip("/") + ".json").get("product")
            if p:
                return shopify.item_from_product(p, base, src)
        except FetchError:
            pass
    return jsonld.parse_page(fetcher.text(url), url, src)


def check(fetcher, profile: dict) -> list[dict]:
    """-> alerts [{url, title, old, new, target, my_sizes}] for real price drops / target hits."""
    rows, alerts = load(), []
    for r in rows:
        try:
            it = _read(fetcher, r["url"])
        except FetchError as e:
            r["last_error"] = str(e)[:200]
            continue
        if not it or it.get("price") is None:
            continue
        new, old = it["price"], r.get("price")
        mine = sizes.my_sizes(it["category"], it.get("sizes_available") or [], profile.get("sizes") or {},
                              it.get("sizes_listed")) if it.get("sizes_available") is not None else None
        hit_target = r.get("target") is not None and new <= float(r["target"]) and (old is None or old > float(r["target"]))
        if (old is not None and new < old) or hit_target:
            alerts.append({"url": r["url"], "title": it["title"], "old": old, "new": new, "target": r.get("target"),
                           "my_sizes": mine})
        r.update(price=new, title=it["title"], checked=now_iso(), last_error=None)
        r["history"] = (r.get("history") or [])[-30:] + [[now_iso(), new]]
    save_json(_path(), rows)
    return alerts

"""Sources turn a shop into a list of normalised items. Two generic adapters ship:

  shopify   any Shopify store: /products.json gives every variant's size label and `available` flag
  jsonld    any shop with a sitemap and schema.org Product JSON-LD on its product pages

An item is a plain dict: id, source, title, brand, url, image, category, garment, price, was, currency, discount,
sizes_available, sizes_listed, colour, product_type, tags, seen_at.

Writing your own adapter: a function `fetch(fetcher, src: dict) -> list[dict]` returning items in that shape.
Register it in ADAPTERS (or pass `adapter: mymodule:fetch` in config) and it gets size filtering, tiers,
ranking, the no-repeat ledger and looks for free.
"""
from __future__ import annotations

import importlib

from . import jsonld, shopify

ADAPTERS = {"shopify": shopify.fetch, "jsonld": jsonld.fetch}


def adapter_for(src: dict):
    kind = src.get("adapter") or src.get("type") or "shopify"
    if kind in ADAPTERS:
        return ADAPTERS[kind]
    if ":" in kind:                     # "package.module:function" — bring your own
        mod, fn = kind.split(":", 1)
        return getattr(importlib.import_module(mod), fn)
    raise ValueError(f"unknown adapter {kind!r} for source {src.get('name')}")

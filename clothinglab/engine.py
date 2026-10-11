"""The pipeline: gather from sources -> keep what's in your size -> tier -> rank -> skip what you've seen.

    items = gather(config)                 # every source, politely
    mine  = in_size(items, profile)        # only in-stock variants in YOUR sizes survive
    ranked = rank(mine, profile, caps)     # discount, brands, fit, colours; your exclusions remove items
"""
from __future__ import annotations

import re
from datetime import date

from . import catalog, sizes, tiers
from .fetch import FetchError, Fetcher
from .sources import adapter_for


def fetcher_from(config: dict) -> Fetcher:
    pol = config.get("politeness") or {}
    return Fetcher(config.get("user_agent", ""), delay=pol.get("delay_seconds", 2.0),
                   timeout=pol.get("timeout_seconds", 20), allow_private=bool(pol.get("allow_private_hosts")))


def gather(config: dict, fetcher: Fetcher | None = None, log=print) -> tuple[list[dict], dict]:
    """-> (items, health). A source that fails is reported, never fatal."""
    f = fetcher or fetcher_from(config)
    items, health = [], {}
    for src in config.get("sources") or []:
        if src.get("enabled") is False:
            continue
        try:
            got = adapter_for(src)(f, src)
            health[src["name"]] = {"ok": True, "items": len(got)}
            items.extend(got)
        except (FetchError, ValueError, KeyError) as e:
            health[src["name"]] = {"ok": False, "error": str(e)[:200]}
            log(f"  ! {src.get('name')}: {e}")
    return items, health


def person_department(profile: dict) -> str:
    """mens | womens | both. Profiles from before departments existed are menswear."""
    d = str(profile.get("department") or "mens").lower()
    return d if d in ("mens", "womens", "both") else "mens"


def in_size(items: list[dict], profile: dict) -> list[dict]:
    sz = profile.get("sizes") or {}
    pdept = person_department(profile)
    ranges = sz.get("ranges") or []
    out = []
    for it in items:
        avail = it.get("sizes_available")
        if avail is None:
            continue                        # size unknown: never shown as "in your size"
        if not catalog.wanted(it.get("department"), pdept):
            continue
        if it.get("range") and it["range"] not in ranges:
            continue                        # a petite/tall/maternity product you didn't ask for
        # which chart: the item's department if it says, else the person's ('both' people: their sizes field says)
        dept = it.get("department") or (pdept if pdept != "both" else sz.get("chart", "mens"))
        mine = sizes.my_sizes(it["category"], avail, sz, it.get("sizes_listed"), it.get("size_scale"), dept)
        if mine:
            out.append({**it, "my_sizes": mine})
    return out


def _excluded(it: dict, profile: dict) -> str | None:
    brands = profile.get("brands") or {}
    blob = f"{it.get('brand', '')} {it.get('title', '')}"
    for b in brands.get("never") or []:
        if re.search(r"\b" + re.escape(str(b)) + r"\b", blob, re.I):
            return f"brand {b}"
    for w in (profile.get("fit") or {}).get("never") or []:
        if catalog.words(it.get("title", ""), [w]):
            return f"fit {w}"
    for c in (profile.get("colours") or {}).get("avoid") or []:
        if catalog.words(it.get("colour", ""), [c]):
            return f"colour {c}"
    return None


def rank(items: list[dict], profile: dict, cap_table: dict | None = None, sale_only: bool = True,
         month: int | None = None) -> list[dict]:
    """Score = discount + liked brands + fit + colours, minus out-of-season. Exclusions remove; nothing is guessed.
    sale_only (default): only reduced items, since a shop's full catalogue isn't a deal. Accessories only when the
    profile asks for them (`accessories: true`), so a tote bag never takes a pick from a jacket."""
    cap_table = cap_table or tiers.caps(None, profile)
    month = month or date.today().month
    want_acc = bool(profile.get("accessories"))
    likes = (profile.get("brands") or {}).get("love") or []
    fit_likes = (profile.get("fit") or {}).get("likes") or []
    palette = (profile.get("colours") or {}).get("palette") or []
    want_tiers = tiers.enabled(profile)
    out = []
    for it in items:
        if _excluded(it, profile):
            continue
        if sale_only and not it.get("discount"):
            continue
        if it.get("category") == "accessory" and not want_acc:
            continue
        tier = tiers.tier_for(it.get("garment", "other"), it.get("price"), cap_table)
        if tier and tier not in want_tiers:
            continue
        why, score = [], 0.0
        d = it.get("discount") or 0.0
        if d:
            score += 60 * d
            why.append(f"{round(d * 100)}% off")
        hit = catalog.words(f"{it.get('brand', '')} {it.get('title', '')}", likes)
        if hit:
            score += 20
            why.append(f"you like {hit[0]}")
        fits = catalog.words(it.get("title", ""), fit_likes)
        if fits:
            score += 6 * len(fits)
            why.append(f"{fits[0]} fit")
        cols = catalog.words(it.get("colour", ""), palette)
        if cols:
            score += 10
            why.append(f"in {cols[0]}")
        off = catalog.out_of_season(it.get("title", ""), month)
        if off:
            score -= 25
        out.append({**it, "tier": tier, "score": round(score, 2), "why": why, **({"off_season": True} if off else {})})
    out.sort(key=lambda x: (-x["score"], x.get("price") or 0))
    return out

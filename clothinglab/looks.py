"""Looks: one per budget tier, from things in stock in your size (or that you already own).

A look is either a dress + shoes, or a top + bottom + shoes (a skirt counts as a bottom), plus a layer (coat or
jacket) if one fits the colours. Menswear profiles only build separates; womenswear tries a dress first and falls
back to separates; "both" tries separates first.

Rules, kept simple so you can predict them:
  - everything is in stock in your size, or something you listed under `wardrobe`;
  - every look has at least one new piece, and owned pieces fill at most two slots;
  - at most one loud colour family per look; neutrals (black, white, grey, stone) go with anything;
  - nothing out of season (no shorts in November);
  - no shoes on sale in your size: the look is top + bottom and says so; nothing else missing is papered over;
  - a tier with no look today is skipped and says so, rather than padded.
"""
from __future__ import annotations

from . import catalog, tiers

SEPARATES = (("top",), ("bottom", "skirt"), ("footwear",))
DRESS = (("dress",), ("footwear",))


def _loud(it: dict) -> set[str]:
    return {f for f in catalog.colour_families(it.get("colour") or it.get("title", "")) if f not in catalog.NEUTRAL_FAMILIES}


def _owned(profile: dict) -> list[dict]:
    out = []
    for w in profile.get("wardrobe") or []:
        cat = w.get("category") or catalog.category(w.get("name", ""))
        if cat in ("top", "bottom", "skirt", "dress", "footwear", "outer"):
            out.append({"title": w.get("name", "?"), "category": cat, "colour": w.get("colour", w.get("name", "")),
                        "owned": True, "price": 0})
    return out


def _fill(pool: list[dict], owned: list[dict], slots) -> list[dict] | None:
    pieces, loud = [], set()
    for cats in slots:
        pick = None
        for it in [x for x in pool if x["category"] in cats] + [o for o in owned if o["category"] in cats]:
            colours = _loud(it)
            if loud and colours and not colours <= loud:
                continue
            pick = it
            break
        if not pick:
            return None
        pieces.append(pick)
        loud |= _loud(pick)
    if sum(1 for p in pieces if p.get("owned")) > 2 or all(p.get("owned") for p in pieces):
        return None
    layer = next((x for x in pool if x["category"] == "outer" and (not _loud(x) or _loud(x) <= loud)), None)
    return pieces + ([layer] if layer else [])


def build(ranked: list[dict], profile: dict) -> list[dict]:
    """-> [{tier, kind, pieces: [...], total, note}] in tier order."""
    dept = str(profile.get("department") or "mens").lower()
    shapes = {"womens": [DRESS, SEPARATES], "both": [SEPARATES, DRESS]}.get(dept, [SEPARATES])
    owned = _owned(profile)
    looks = []
    for tier in tiers.enabled(profile):
        pool = [it for it in ranked if it.get("tier") == tier and not it.get("off_season")]
        pieces = next((p for p in (_fill(pool, owned, shape) for shape in shapes) if p), None)
        note = ""
        if not pieces:                      # no shoes on sale in your size is common; still worth a look
            pieces = next((p for p in (_fill(pool, owned, shape[:-1]) for shape in shapes if len(shape) > 2) if p), None)
            note = "no shoes in your size on sale today" if pieces else ""
        if not pieces:
            looks.append({"tier": tier, "pieces": [], "total": 0,
                          "note": f"no full {tiers.LABEL[tier]} look in your size today"})
            continue
        looks.append({"tier": tier, "pieces": pieces, "total": round(sum(p.get("price") or 0 for p in pieces), 2),
                      "note": note})
    return looks

"""Looks: a top, a bottom and shoes (and a layer if there's one), one look per budget tier.

Rules, kept deliberately simple so you can predict them:
  - everything in the look is in stock in your size (or something you already own, from profile `wardrobe`);
  - every look has at least one new piece, and owned pieces fill at most two slots;
  - at most one loud colour per look; neutrals (black, white, grey, stone) go with anything;
  - a tier with no top, bottom AND shoes in your size today is skipped and says so, rather than padded.
"""
from __future__ import annotations

from . import catalog, tiers

SLOTS = ("top", "bottom", "footwear")


def _loud(it: dict) -> set[str]:
    return {f for f in catalog.colour_families(it.get("colour") or it.get("title", "")) if f not in catalog.NEUTRAL_FAMILIES}


def _owned(profile: dict) -> list[dict]:
    out = []
    for w in profile.get("wardrobe") or []:
        cat = w.get("category") or catalog.category(w.get("name", ""))
        if cat in ("top", "bottom", "footwear", "outer"):
            out.append({"title": w.get("name", "?"), "category": cat, "colour": w.get("colour", w.get("name", "")),
                        "owned": True, "price": 0})
    return out


def build(ranked: list[dict], profile: dict) -> list[dict]:
    """-> [{tier, pieces: [...], total, note}] in tier order."""
    owned = _owned(profile)
    looks = []
    for tier in tiers.enabled(profile):
        pool = [it for it in ranked if it.get("tier") == tier]
        pieces, loud = [], set()
        for slot in SLOTS:
            pick = None
            for it in [x for x in pool if x["category"] == slot] + [o for o in owned if o["category"] == slot]:
                colours = _loud(it)
                if loud and colours and not colours <= loud:
                    continue
                pick = it
                break
            if not pick:
                break
            pieces.append(pick)
            loud |= _loud(pick)
        if len(pieces) < len(SLOTS):
            looks.append({"tier": tier, "pieces": [], "total": 0, "note": f"no full {tiers.LABEL[tier]} look in your size today"})
            continue
        if sum(1 for p in pieces if p.get("owned")) > 2 or all(p.get("owned") for p in pieces):
            looks.append({"tier": tier, "pieces": [], "total": 0, "note": "only owned pieces fitted; skipped"})
            continue
        layer = next((x for x in pool if x["category"] == "outer" and (not _loud(x) or _loud(x) <= loud)), None)
        if layer:
            pieces.append(layer)
        looks.append({"tier": tier, "pieces": pieces, "total": round(sum(p.get("price") or 0 for p in pieces), 2),
                      "note": ""})
    return looks

"""Budget tiers: 💸 low / 👌 mid / 💎 high, by ABSOLUTE price per garment type.

A percentile would drift with whatever happens to be on sale; a £ line per garment is something a person can read,
argue with and change. Below `low` is low, above `high` is high, in between is mid. Defaults come from a few weeks
of UK menswear sale prices; override them in config.yaml (`tiers.caps`) or per person in profile.yaml
(`budget.caps`).
"""
from __future__ import annotations

TIERS = ("low", "mid", "high")
EMOJI = {"low": "💸", "mid": "👌", "high": "💎"}
LABEL = {"low": "Low", "mid": "Mid", "high": "High"}

DEFAULT_CAPS = {
    "tee": {"low": 25, "high": 80},
    "hoodie": {"low": 35, "high": 115},
    "knit": {"low": 25, "high": 165},
    "shirt": {"low": 45, "high": 120},
    "jacket": {"low": 65, "high": 175},
    "trousers": {"low": 40, "high": 125},
    "denim": {"low": 30, "high": 85},
    "track": {"low": 25, "high": 70},
    "trainers": {"low": 65, "high": 210},
    "other": {"low": 35, "high": 125},
}


def caps(config: dict | None = None, profile: dict | None = None) -> dict:
    out = {g: dict(v) for g, v in DEFAULT_CAPS.items()}
    for src in ((config or {}).get("tiers", {}).get("caps"), (profile or {}).get("budget", {}).get("caps")):
        for g, v in (src or {}).items():
            out.setdefault(g, {}).update({k: float(x) for k, x in (v or {}).items() if k in ("low", "high")})
    return out


def enabled(profile: dict | None = None) -> list[str]:
    want = (profile or {}).get("budget", {}).get("tiers") or list(TIERS)
    return [t for t in TIERS if t in want]


def tier_for(garment: str, price: float | None, cap_table: dict) -> str | None:
    if price is None:
        return None
    c = cap_table.get(garment) or cap_table["other"]
    if price <= c["low"]:
        return "low"
    if price > c["high"]:
        return "high"
    return "mid"


def badge(tier: str | None) -> str:
    return f"{EMOJI[tier]} {LABEL[tier]}" if tier in EMOJI else ""

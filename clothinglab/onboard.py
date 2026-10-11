"""The onboarding interview: a short set of questions -> a validated profile.yaml.

The agent (or the CLI) asks the questions, writes the person's answers into an answers dict in THEIR words, and
build() turns that into a profile. Nothing is invented: a missing answer stays empty. It never asks for height,
weight or body measurements beyond what sizes need, and it never looks at photos of the person.
"""
from __future__ import annotations

import re
from datetime import date

from . import sizes as S
from .tiers import DEFAULT_CAPS, TIERS

SECTIONS = [
    {"id": "sizes", "title": "Sizes", "intro": "Sizes first, so nothing out of size ever reaches you.", "questions": [
        {"id": "tops", "field": "sizes.tops", "type": "letters", "required": True,
         "ask": "What size do you take in tops, hoodies and jackets? Best fit first (e.g. M, or L and XL)."},
        {"id": "waist", "field": "sizes.waist", "type": "ints:24-54", "required": True,
         "ask": "Waist in inches for jeans and trousers? One or two numbers (e.g. 32, or 32 and 33)."},
        {"id": "length", "field": "sizes.trouser_length", "type": "choice:short|regular|long",
         "ask": "Trouser length: short, regular or long? (Skip if any is fine.)"},
        {"id": "bottoms_letter", "field": "sizes.bottoms_letter", "type": "letters",
         "ask": "For joggers and shorts sold as S/M/L, which letters fit you?"},
        {"id": "shoes", "field": "sizes.shoes_uk", "type": "shoes", "required": True,
         "ask": "UK shoe size? Half sizes are fine (e.g. 9 or 9.5). EU and US are worked out for you."},
    ]},
    {"id": "fit", "title": "Fit", "intro": "How you like things to sit.", "questions": [
        {"id": "fit_likes", "field": "fit.likes", "type": "list", "required": True,
         "ask": "Which fits do you like? (relaxed, oversized, boxy, regular, straight, wide…)"},
        {"id": "fit_never", "field": "fit.never", "type": "list",
         "ask": "Any cuts you never wear? (e.g. skinny, slim, cropped)"},
    ]},
    {"id": "colours", "title": "Colours", "intro": "", "questions": [
        {"id": "palette", "field": "colours.palette", "type": "list", "required": True,
         "ask": "Which colours do you wear most?"},
        {"id": "avoid", "field": "colours.avoid", "type": "list", "ask": "Colours you never wear?"},
    ]},
    {"id": "brands", "title": "Brands", "intro": "", "questions": [
        {"id": "love", "field": "brands.love", "type": "list", "ask": "Brands you love or would buy without thinking?"},
        {"id": "never", "field": "brands.never", "type": "list",
         "ask": "Brands or shops that never fit you or you won't buy? They'll never be shown."},
    ]},
    {"id": "budget", "title": "Budget", "intro": "Three tiers: 💸 Low, 👌 Mid, 💎 High.", "questions": [
        {"id": "tiers", "field": "budget.tiers", "type": "tiers", "ask": "Which tiers do you want to see? (any of low, mid, high)"},
        {"id": "caps", "field": "budget.caps", "type": "caps",
         "ask": "Want to move any price lines? e.g. 'tees low under 20, trainers high over 180'. Skip to keep the defaults."},
    ]},
    {"id": "wardrobe", "title": "What you own", "intro": "Optional: looks can work around pieces you already love.",
     "questions": [
         {"id": "wardrobe", "field": "wardrobe", "type": "wardrobe",
          "ask": "Any pieces you own that looks should use? e.g. 'navy chore jacket, white leather trainers'."},
     ]},
    {"id": "delivery", "title": "Delivery", "intro": "", "questions": [
        {"id": "name", "field": "name", "type": "text", "ask": "What should the digest call you? (first name or a nickname)"},
    ]},
]


def questions() -> list[dict]:
    return SECTIONS


def _split(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in re.split(r",|\band\b|/|;", str(v)) if x.strip()]


def _get(d: dict, dotted: str):
    cur = d
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _set(d: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    cur = d
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value


def _caps(v) -> dict:
    if isinstance(v, dict):
        return v
    out = {}
    for m in re.finditer(r"(\w+?)s?\s+(low|high)\s+(?:under|over|at|=)?\s*£?(\d+(?:\.\d+)?)", str(v or ""), re.I):
        g = m.group(1).lower()
        g = {"t-shirt": "tee", "tshirt": "tee", "jean": "denim", "trainer": "trainers", "shoe": "trainers"}.get(g, g)
        if g in DEFAULT_CAPS:
            out.setdefault(g, {})[m.group(2).lower()] = float(m.group(3))
    return out


def _wardrobe(v) -> list[dict]:
    from .catalog import category
    out = []
    for name in _split(v):
        out.append({"name": name, "category": category(name)})
    return out


def coerce(q: dict, raw):
    t = q["type"]
    if raw in (None, "", []):
        return None
    if t == "letters":
        return S.norm_letters(_split(raw))
    if t.startswith("ints:"):
        lo, hi = map(int, t.split(":")[1].split("-"))
        return [int(x) for x in re.findall(r"\d+", str(raw)) if lo <= int(x) <= hi] or None
    if t.startswith("choice:"):
        opts = t.split(":")[1].split("|")
        v = str(raw).strip().lower()
        return v if v in opts else None
    if t == "shoes":
        return [float(x) for x in re.findall(r"\d{1,2}(?:\.5)?", str(raw)) if 3 <= float(x) <= 16] or None
    if t == "list":
        return _split(raw)
    if t == "tiers":
        return [x for x in TIERS if x in [s.lower() for s in _split(raw)]] or None
    if t == "caps":
        return _caps(raw) or None
    if t == "wardrobe":
        return _wardrobe(raw)
    return str(raw).strip()


def build(answers: dict) -> tuple[dict, list[str]]:
    """answers: {question_id: raw answer} or a nested dict keyed by field. -> (profile, problems)."""
    prof: dict = {"schema_version": 1, "created": date.today().isoformat()}
    problems = []
    for sec in SECTIONS:
        for q in sec["questions"]:
            raw = answers.get(q["id"]) if q["id"] in answers else _get(answers, q["field"])
            val = coerce(q, raw)
            if val is None:
                if q.get("required"):
                    problems.append(f"missing or unreadable: {q['id']} ({q['ask']})")
                continue
            _set(prof, q["field"], val)
    return prof, problems + validate(prof)


def validate(prof: dict) -> list[str]:
    p = []
    sz = prof.get("sizes") or {}
    if not sz.get("tops"):
        p.append("sizes.tops is empty")
    if not sz.get("waist") and not sz.get("bottoms_letter"):
        p.append("need sizes.waist or sizes.bottoms_letter")
    if not sz.get("shoes_uk"):
        p.append("sizes.shoes_uk is empty")
    for t in (prof.get("budget") or {}).get("tiers") or []:
        if t not in TIERS:
            p.append(f"unknown tier {t}")
    for k in ("height", "weight", "chest", "body"):
        if k in prof or k in (prof.get("sizes") or {}):
            p.append(f"profile must not store {k}")
    return p

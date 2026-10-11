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

ALL, M, W = ("mens", "womens", "both"), ("mens", "both"), ("womens", "both")

SECTIONS = [
    {"id": "department", "title": "What you shop for", "intro": "", "questions": [
        {"id": "department", "field": "department", "type": "choice:mens|womens|both", "required": ALL, "for": ALL,
         "ask": "Should I look at menswear, womenswear, or both?"},
        {"id": "chart", "field": "sizes.chart", "type": "choice:mens|womens", "for": ("both",),
         "ask": "For shoes and jeans, do you usually buy from the men's or women's size chart?"},
    ]},
    {"id": "sizes", "title": "Sizes", "intro": "Sizes first, so nothing out of size ever reaches you.", "questions": [
        {"id": "tops", "field": "sizes.tops", "type": "letters", "required": M, "for": ALL,
         "ask": "Letter size for tops, knitwear and jackets? Best fit first (e.g. M, or L and XL)."},
        {"id": "dress", "field": "sizes.dress_uk", "type": "dress", "required": ("womens",), "for": W,
         "ask": "UK dress size? One or two (e.g. 10, or 10 and 12). EU and US sizes are worked out for you."},
        {"id": "waist", "field": "sizes.waist", "type": "ints:22-54", "required": ("mens",), "for": ALL,
         "ask": "Jeans waist in inches, if you buy by waist (e.g. 28, or 32 and 33)?"},
        {"id": "length", "field": "sizes.trouser_length", "type": "choice:short|regular|long", "for": ALL,
         "ask": "Leg length: short, regular or long? (Skip if any is fine.)"},
        {"id": "bottoms_letter", "field": "sizes.bottoms_letter", "type": "letters", "for": ALL,
         "ask": "For joggers, shorts and skirts sold as S/M/L, which letters fit you?"},
        {"id": "ranges", "field": "sizes.ranges", "type": "ranges", "for": W,
         "ask": "Do you shop petite, tall or maternity ranges? (Skip if not; those items are then left out.)"},
        {"id": "shoes", "field": "sizes.shoes_uk", "type": "shoes", "required": ALL, "for": ALL,
         "ask": "UK shoe size? Half sizes are fine (e.g. 5 or 5.5). EU and US are worked out for you."},
    ]},
    {"id": "fit", "title": "Fit", "intro": "How you like things to sit.", "questions": [
        {"id": "fit_likes", "field": "fit.likes", "type": "list", "required": ALL, "for": ALL,
         "ask": "Which fits or shapes do you like? (relaxed, oversized, straight, wide-leg, midi, wrap…)"},
        {"id": "fit_never", "field": "fit.never", "type": "list", "for": ALL,
         "ask": "Any cuts you never wear? (e.g. skinny, cropped, bodycon)"},
    ]},
    {"id": "colours", "title": "Colours", "intro": "", "questions": [
        {"id": "palette", "field": "colours.palette", "type": "list", "required": ALL, "for": ALL,
         "ask": "Which colours do you wear most?"},
        {"id": "avoid", "field": "colours.avoid", "type": "list", "for": ALL, "ask": "Colours you never wear?"},
    ]},
    {"id": "brands", "title": "Brands", "intro": "", "questions": [
        {"id": "love", "field": "brands.love", "type": "list", "for": ALL,
         "ask": "Brands you love or would buy without thinking?"},
        {"id": "never", "field": "brands.never", "type": "list", "for": ALL,
         "ask": "Brands or shops that never fit you or you won't buy? They'll never be shown."},
    ]},
    {"id": "budget", "title": "Budget", "intro": "Three tiers: 💸 Low, 👌 Mid, 💎 High.", "questions": [
        {"id": "tiers", "field": "budget.tiers", "type": "tiers", "for": ALL,
         "ask": "Which tiers do you want to see? (any of low, mid, high)"},
        {"id": "caps", "field": "budget.caps", "type": "caps", "for": ALL,
         "ask": "Want to move any price lines? e.g. 'dresses low under 30, boots high over 150'. Skip to keep the defaults."},
    ]},
    {"id": "wardrobe", "title": "What you own", "intro": "Optional: looks can work around pieces you already love.",
     "questions": [
         {"id": "wardrobe", "field": "wardrobe", "type": "wardrobe", "for": ALL,
          "ask": "Any pieces you own that looks should use? e.g. 'navy wool coat, white leather trainers'."},
     ]},
    {"id": "delivery", "title": "Delivery", "intro": "", "questions": [
        {"id": "name", "field": "name", "type": "text", "for": ALL,
         "ask": "What should the digest call you? (first name or a nickname)"},
    ]},
]


def questions(department: str | None = None) -> list[dict]:
    """All sections, or only the questions that apply to one department (ask `department` first)."""
    if department not in ALL:
        return SECTIONS
    out = []
    for sec in SECTIONS:
        qs = [q for q in sec["questions"] if department in q["for"]]
        if qs:
            out.append({**sec, "questions": qs})
    return out


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
    alias = {"t-shirt": "tee", "tshirt": "tee", "jean": "denim", "jeans": "denim", "trainer": "trainers",
             "shoe": "trainers", "boot": "boots", "coat": "jacket"}
    for m in re.finditer(r"([a-z-]+)\s+(low|high)\s+(?:under|over|at|=)?\s*£?(\d+(?:\.\d+)?)", str(v or ""), re.I):
        w = m.group(1).lower()
        g = next((c for c in (w, alias.get(w), re.sub(r"es$", "", w), re.sub(r"s$", "", w)) if c in DEFAULT_CAPS), None)
        if g:
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
    if t == "choice:mens|womens|both":
        v = str(raw).lower()
        if "both" in v or ("women" in v and re.search(r"\bmen", v)):
            return "both"
        if re.search(r"wom[ae]n|ladies|female", v):
            return "womens"
        if re.search(r"\bmen|male", v):
            return "mens"
        return None
    if t.startswith("choice:"):
        opts = t.split(":")[1].split("|")
        v = str(raw).strip().lower()
        return v if v in opts else None
    if t == "dress":
        return [int(x) for x in re.findall(r"\d{1,2}", str(raw)) if int(x) in range(4, 28, 2)] or None
    if t == "ranges":
        return [x for x in ("petite", "tall", "maternity") if x in str(raw).lower()] or None
    if t == "shoes":
        return [float(x) for x in re.findall(r"\d{1,2}(?:\.5)?", str(raw)) if 2 <= float(x) <= 16] or None
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
    prof: dict = {"schema_version": 2, "created": date.today().isoformat()}
    problems = []
    dept_q = SECTIONS[0]["questions"][0]
    raw_dept = answers.get("department") if "department" in answers else _get(answers, "department")
    dept = coerce(dept_q, raw_dept) or "mens"
    for sec in SECTIONS:
        for q in sec["questions"]:
            if dept not in q["for"]:
                continue
            raw = answers.get(q["id"]) if q["id"] in answers else _get(answers, q["field"])
            val = coerce(q, raw)
            if val is None:
                if dept in (q.get("required") or ()):
                    problems.append(f"missing or unreadable: {q['id']} ({q['ask']})")
                continue
            _set(prof, q["field"], val)
    prof.setdefault("department", dept)
    return prof, problems + validate(prof)


def validate(prof: dict) -> list[str]:
    p = []
    dept = prof.get("department", "mens")
    if dept not in ALL:
        p.append(f"department must be one of {', '.join(ALL)}")
    sz = prof.get("sizes") or {}
    if dept == "mens" and not sz.get("tops"):
        p.append("sizes.tops is empty")
    if dept in ("womens", "both") and not (sz.get("tops") or sz.get("dress_uk")):
        p.append("need sizes.dress_uk or sizes.tops")
    if dept == "mens" and not sz.get("waist") and not sz.get("bottoms_letter"):
        p.append("need sizes.waist or sizes.bottoms_letter")
    if not sz.get("shoes_uk"):
        p.append("sizes.shoes_uk is empty")
    for t in (prof.get("budget") or {}).get("tiers") or []:
        if t not in TIERS:
            p.append(f"unknown tier {t}")
    for k in ("height", "weight", "chest", "body", "bust", "hips"):
        if k in prof or k in sz:
            p.append(f"profile must not store {k}")
    for v in (prof.get("name"), *(sz.values() if isinstance(sz, dict) else [])):
        if isinstance(v, str) and "TODO" in v:
            p.append("profile still has TODO values")
            break
    return p

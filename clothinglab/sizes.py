"""Size matching: is this variant label one of MY sizes?

Everything here is driven by the profile, nothing is hard-coded to one person. The hard parts are real-world
labels: "XX-Large", "2XL", "W32 L30", "32R", "46 2/3 / Cream / Blue" (Shopify glues size and colour into one
variant label), bare EU numbers on European stores, and youth sizes that look like adult ones ("6Y", "5.5 GS").
"""
from __future__ import annotations

import re

LETTERS = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "3XL", "4XL"]
_LETTER_ALIASES = [
    (r"(?:4xl|xxxxl|4x-?large)", "4XL"),
    (r"(?:3xl|xxxl|3x-?large|xxx-?large)", "3XL"),
    (r"(?:xxl|2xl|xx-?large|2x-?large|extra[ -]?extra[ -]?large)", "XXL"),
    (r"(?:xl|x-?large|extra[ -]?large)", "XL"),
    (r"(?:xxs|xx-?small|2xs)", "XXS"),
    (r"(?:xs|x-?small|extra[ -]?small)", "XS"),
    (r"(?:l|large|lg)", "L"),
    (r"(?:m|medium|med)", "M"),
    (r"(?:s|small|sm)", "S"),
]
_LETTER_RES = [(re.compile(r"^(?:size\s*)?" + p + r"(?![a-z])", re.I), v) for p, v in _LETTER_ALIASES]


def letter(label: str) -> str | None:
    """'XX-Large' -> 'XXL', 'Size L / Black' -> 'L', '32' -> None."""
    s = (label or "").strip()
    for rx, v in _LETTER_RES:
        if rx.match(s):
            return v
    return None


def norm_letters(values) -> list[str]:
    out = []
    for v in values or []:
        n = letter(str(v))
        if n and n not in out:
            out.append(n)
    return out


# ------------------------------------------------------------------ waist / trousers
_WAIST_LEN = re.compile(
    r"^\s*(?:w\s*)?(\d{2})\s*(?:(?:\"|in|inch(?:es)?)?\s*(?:[x/]|\s)?\s*(?:l\s*)?(\d{2})\b|"
    r"\s*(r|reg|regular|s|short|l|long)\b)?", re.I)
_LEN_WORD = {"r": "regular", "reg": "regular", "regular": "regular", "s": "short", "short": "short",
             "l": "long", "long": "long"}


def waist(label: str) -> tuple[int, str | None] | None:
    """'W32 L30' -> (32, 'short'), '32R' -> (32, 'regular'), '34' -> (34, None), 'M' -> None."""
    m = _WAIST_LEN.match((label or "").replace(",", " "))
    if not m:
        return None
    w = int(m.group(1))
    if not 22 <= w <= 60:
        return None
    length = None
    if m.group(2):
        leg = int(m.group(2))
        length = "short" if leg <= 30 else ("regular" if leg <= 32 else "long")
    elif m.group(3):
        length = _LEN_WORD[m.group(3).lower()]
    return w, length


# ------------------------------------------------------------------ shoes
SHOE_YOUTH = re.compile(r"^\s*\d{1,2}(?:\.5)?\s*(?:y|k|c|gs|td|ps|kids?|junior|infant)\b", re.I)
# Men's UK -> EU, the common trainer chart (Nike/adidas sit within half a size of this).
UK_TO_EU = {5: 38.5, 5.5: 39, 6: 40, 6.5: 40.5, 7: 41, 7.5: 42, 8: 42.5, 8.5: 43, 9: 44, 9.5: 44.5, 10: 45,
            10.5: 45.5, 11: 46, 11.5: 47, 12: 47.5, 12.5: 48, 13: 48.5, 14: 49.5, 15: 50.5}


def _fractions(s: str) -> str:
    s = re.sub(r"(\d)\s*1/3", r"\1.33", s)
    s = re.sub(r"(\d)\s*2/3", r"\1.67", s)
    s = re.sub(r"(\d)\s*1/2", r"\1.5", s)
    return s.replace("⅓", ".33").replace("⅔", ".67").replace("½", ".5")


def shoe(label: str) -> tuple[str | None, float] | None:
    """('uk'|'eu'|'us'|None, number). None scale = a bare number; youth sizes are rejected outright."""
    s = _fractions((label or "").strip().lower().replace(",", "."))
    if not s or SHOE_YOUTH.match(s):
        return None
    m = re.search(r"\b(uk|eu|eur|us)\s*(\d{1,2}(?:\.\d{1,2})?)", s)
    if m:
        return ("eu" if m.group(1).startswith("eu") else m.group(1)), float(m.group(2))
    m = re.match(r"\s*(?:size\s*)?(\d{1,2}(?:\.\d{1,2})?)(?![\d.])", s)
    return (None, float(m.group(1))) if m else None


def shoe_scale(labels, hint: str | None = None) -> str:
    """Which number system a store lists in. EU is provable from the range (no adult UK/US size is 39+);
    UK vs US is not, so a bare list is UK unless the source config says otherwise."""
    if hint in ("uk", "eu", "us"):
        return hint
    nums = [p[1] for p in (shoe(x) for x in labels or []) if p and p[0] is None]
    return "eu" if nums and max(nums) >= 39 else "uk"


def eu_window(uk_sizes) -> tuple[float, float] | None:
    eus = [UK_TO_EU[float(u)] for u in uk_sizes if float(u) in UK_TO_EU]
    return (min(eus) - 0.5, max(eus)) if eus else None


def shoe_ok(label: str, uk_sizes, scale: str = "uk") -> bool:
    p = shoe(label)
    if not p or not uk_sizes:
        return False
    sc, n = p
    sc = sc or scale
    uk = {float(u) for u in uk_sizes}
    if sc == "eu":
        w = eu_window(uk)
        return bool(w) and w[0] <= n <= w[1]
    if sc == "us":
        return (n - 1) in uk
    return n in uk


# ------------------------------------------------------------------ the one entry point
def in_my_size(category: str | None, label: str, sizes: dict, scale: str = "uk") -> bool:
    """sizes = profile['sizes']: tops, bottoms_letter, waist, trouser_length, shoes_uk."""
    lab = (label or "").strip()
    if not lab or not category:
        return False
    if category == "footwear":
        return shoe_ok(lab, sizes.get("shoes_uk") or [], scale)
    if category in ("top", "outer", "set"):
        return letter(lab) in norm_letters(sizes.get("tops"))
    if category == "bottom":
        w = waist(lab)
        if w:
            want_len = sizes.get("trouser_length")
            return w[0] in {int(x) for x in sizes.get("waist") or []} and (not want_len or not w[1] or w[1] == want_len)
        return letter(lab) in norm_letters(sizes.get("bottoms_letter"))
    if category == "accessory":
        return bool(re.search(r"one ?size|o/s|\bos\b|adjustable", lab, re.I))
    return False


def my_sizes(category: str | None, available: list[str], sizes: dict, listed: list[str] | None = None,
             hint: str | None = None) -> list[str]:
    """The in-stock labels that fit, with bare EU numbers stamped 'EU 44' so people see what they'd order."""
    scale = shoe_scale((listed or []) + list(available), hint) if category == "footwear" else "uk"
    out = []
    for lab in available:
        if in_my_size(category, lab, sizes, scale):
            p = shoe(lab) if category == "footwear" else None
            if p and p[0] is None and scale == "eu":
                lab = f"EU {lab.split('/')[0].strip()}"
            out.append(lab.strip())
    return out

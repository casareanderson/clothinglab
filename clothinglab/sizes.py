"""Size matching: is this variant label one of MY sizes?

Everything is driven by the profile, nothing is hard-coded to one person. The hard parts are real-world labels:
"XX-Large", "2XL", "W32 L30", "32R", "S/10", "UK 10", "EU 38", "10 Petite", "46 2/3 / Cream / Blue" (Shopify glues
size and colour into one label), bare EU shoe numbers, and youth sizes that look like adult ones ("6Y", "5.5 GS").

Departments: men's and women's use different charts for the same number, so every check takes `dept`
("mens" | "womens"). The profile's `department` decides which charts apply to the person.
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

RANGES = ("petite", "tall", "maternity")
_RANGE_RE = re.compile(r"\b(petite|tall|maternity|regular)\b", re.I)


def letter(label: str) -> str | None:
    """'XX-Large' -> 'XXL', 'Size L / Black' -> 'L', 'S/10' -> 'S', '32' -> None."""
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


def label_range(label: str) -> str | None:
    """'10 Petite' / 'M / Tall' -> 'petite' / 'tall'. 'Regular' is the normal range -> None."""
    m = _RANGE_RE.search(label or "")
    return None if not m or m.group(1).lower() == "regular" else m.group(1).lower()


def strip_range(label: str) -> str:
    return re.sub(r"\s*[/|-]?\s*\b(petite|tall|maternity|regular)\b\s*", " ", label or "", flags=re.I).strip(" /|-")


# ------------------------------------------------------------------ trousers: waist + leg
_WAIST_LEN = re.compile(
    r"^\s*(?:w\s*)?(\d{2})\s*(?:(?:\"|in|inch(?:es)?)?\s*(?:[x/]|\s)?\s*(?:l\s*)?(\d{2})\b|"
    r"\s*(r|reg|regular|s|short|l|long)\b)?", re.I)
_LEN_WORD = {"r": "regular", "reg": "regular", "regular": "regular", "s": "short", "short": "short",
             "l": "long", "long": "long"}


def leg_class(leg: int, dept: str = "mens") -> str:
    """Inside-leg inches -> short/regular/long. Women's legs run shorter: a 30" leg is short on men's jeans
    and regular on women's (the usual UK retailer split: women 28-29 short, 30-31 regular, 32+ long)."""
    if dept == "womens":
        return "short" if leg <= 29 else ("regular" if leg <= 31 else "long")
    return "short" if leg <= 30 else ("regular" if leg <= 32 else "long")


def waist(label: str, dept: str = "mens") -> tuple[int, str | None] | None:
    """'W32 L30' -> (32, 'short'), '32R' -> (32, 'regular'), '34' -> (34, None), 'M' -> None."""
    m = _WAIST_LEN.match((label or "").replace(",", " "))
    if not m:
        return None
    w = int(m.group(1))
    if not 22 <= w <= 60:
        return None
    length = None
    if m.group(2):
        length = leg_class(int(m.group(2)), dept)
    elif m.group(3):
        length = _LEN_WORD[m.group(3).lower()]
    return w, length


# ------------------------------------------------------------------ women's clothing sizes
# UK women's dress sizes and their EU / US equivalents: the conversion printed on UK high-street women's size
# guides (UK 8 = EU 36 = US 4, UK 10 = EU 38 = US 6, UK 12 = EU 40 = US 8). EU = UK + 28, US = UK - 4.
# Brands run large or small; this converts labels, it doesn't fix vanity sizing.
UK_DRESS = list(range(4, 28, 2))


def dress(label: str) -> tuple[str | None, int, str | None] | None:
    """('uk'|'eu'|'us'|None, number, length-word) for women's clothing labels, or None.
    'UK 10' -> ('uk', 10, None), 'EU 38', 'US 6', '10' -> (None, 10, None), 'S/10' -> (None, 10, None),
    '10R' -> (None, 10, 'regular'), '8-10' -> (None, 8, None) (the range is handled by dress_ok)."""
    s = strip_range(label).lower()
    m = re.search(r"\b(uk|eu|eur|us)\s*(\d{1,2})\b", s)
    if m:
        return ("eu" if m.group(1).startswith("eu") else m.group(1)), int(m.group(2)), None
    m = re.search(r"(?:^|/|\s)(\d{1,2})\s*(r|reg|regular|s|short|l|long)?\b(?!\s*[x/]\s*\d)", s)
    if not m or re.match(r"^\s*w\s*\d", s):
        return None
    return None, int(m.group(1)), _LEN_WORD.get((m.group(2) or "").lower())


def dress_to_uk(scale: str | None, n: int) -> int | None:
    if scale == "eu" or (scale is None and n >= 30):
        uk = n - 28
    elif scale == "us":
        uk = n + 4
    else:
        uk = n
    return uk if uk in UK_DRESS else None


def dress_ok(label: str, uk_sizes) -> bool:
    """'8-10' matches someone who's a 10. Bare numbers are UK unless they're 30+ (EU)."""
    if not uk_sizes:
        return False
    want = {int(x) for x in uk_sizes}
    s = strip_range(label).lower()
    rng = re.search(r"\b(?:uk\s*)?(\d{1,2})\s*[-–/]\s*(\d{1,2})\b", s)
    if rng and not re.search(r"\b(?:eu|us)\b", s) and int(rng.group(2)) - int(rng.group(1)) in (2, 4):
        return any(int(rng.group(1)) <= w <= int(rng.group(2)) for w in want)
    d = dress(s)
    return bool(d) and dress_to_uk(d[0], d[1]) in want


# ------------------------------------------------------------------ shoes
SHOE_YOUTH = re.compile(r"^\s*\d{1,2}(?:\.5)?\s*(?:y|k|c|gs|td|ps|kids?|junior|infant)\b", re.I)
# Men's UK -> EU: the common trainer chart (Nike/adidas sit within half a size of this). US men's = UK + 1.
UK_TO_EU_MENS = {5: 38.5, 5.5: 39, 6: 40, 6.5: 40.5, 7: 41, 7.5: 42, 8: 42.5, 8.5: 43, 9: 44, 9.5: 44.5, 10: 45,
                 10.5: 45.5, 11: 46, 11.5: 47, 12: 47.5, 12.5: 48, 13: 48.5, 14: 49.5, 15: 50.5}
# Women's UK -> EU: the common UK shoe-retailer women's chart (UK 4 = EU 37, UK 5 = EU 38, UK 6 = EU 39). US women's
# = UK + 2. Brands differ by half a size (trainer brands often run UK 5 = EU 38.5), hence the tolerance below.
UK_TO_EU_WOMENS = {2: 35, 2.5: 35.5, 3: 36, 3.5: 36.5, 4: 37, 4.5: 37.5, 5: 38, 5.5: 38.5, 6: 39, 6.5: 40,
                   7: 40.5, 7.5: 41, 8: 42, 8.5: 42.5, 9: 43}
US_OFFSET = {"mens": 1.0, "womens": 2.0}


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
    """Which number system a shop lists shoes in. EU is provable from the numbers: no adult UK or US shoe is 30+,
    and every adult EU size is (women's EU starts around 35, so a men's-only '39+' rule would miss them).
    UK vs US is NOT provable, so a bare list is UK unless the source says `shoe_scale: us`."""
    if hint in ("uk", "eu", "us"):
        return hint
    nums = [p[1] for p in (shoe(x) for x in labels or []) if p and p[0] is None]
    return "eu" if nums and max(nums) >= 30 else "uk"


def eu_window(uk_sizes, dept: str = "mens") -> tuple[float, float] | None:
    chart = UK_TO_EU_WOMENS if dept == "womens" else UK_TO_EU_MENS
    eus = [chart[float(u)] for u in uk_sizes if float(u) in chart]
    return (min(eus) - 0.5, max(eus)) if eus else None


def shoe_ok(label: str, uk_sizes, scale: str = "uk", dept: str = "mens") -> bool:
    p = shoe(label)
    if not p or not uk_sizes:
        return False
    sc, n = p
    sc = sc or scale
    uk = {float(u) for u in uk_sizes}
    if sc == "eu":
        w = eu_window(uk, dept)
        return bool(w) and w[0] <= n <= w[1]
    if sc == "us":
        return (n - US_OFFSET.get(dept, 1.0)) in uk
    return n in uk


# ------------------------------------------------------------------ the one entry point
CLOTHING = ("top", "outer", "set", "dress", "skirt")


def in_my_size(category: str | None, label: str, sizes: dict, scale: str = "uk", dept: str = "mens") -> bool:
    """sizes = profile['sizes']: tops, dress_uk, bottoms_letter, waist, trouser_length, shoes_uk, ranges."""
    lab = (label or "").strip()
    if not lab or not category:
        return False
    rng = label_range(lab)
    if rng and rng not in (sizes.get("ranges") or []):
        return False                                   # a petite/tall/maternity variant you didn't ask for
    lab = strip_range(lab) or lab
    if category == "footwear":
        return shoe_ok(lab, sizes.get("shoes_uk") or [], scale, dept)
    if category in CLOTHING:
        if letter(lab) and letter(lab) in norm_letters(sizes.get("tops")):
            return True
        return dept == "womens" and dress_ok(lab, sizes.get("dress_uk"))
    if category == "bottom":
        want_len = sizes.get("trouser_length")
        w = waist(lab, dept)
        if w and not (dept == "womens" and w[0] <= 26 and not re.match(r"^\s*w", lab, re.I)):
            return w[0] in {int(x) for x in sizes.get("waist") or []} and (not want_len or not w[1] or w[1] == want_len)
        if letter(lab):
            return letter(lab) in norm_letters(sizes.get("bottoms_letter") or sizes.get("tops"))
        if dept == "womens" and dress_ok(lab, sizes.get("dress_uk")):
            d = dress(lab)
            return not (want_len and d and d[2] and d[2] != want_len)
        return False
    if category == "accessory":
        return bool(re.search(r"one ?size|o/s|\bos\b|adjustable", lab, re.I))
    return False


def my_sizes(category: str | None, available: list[str], sizes: dict, listed: list[str] | None = None,
             hint: str | None = None, dept: str = "mens") -> list[str]:
    """The in-stock labels that fit, with bare EU shoe numbers stamped 'EU 38' so people see what they'd order."""
    scale = shoe_scale((listed or []) + list(available), hint) if category == "footwear" else "uk"
    out = []
    for lab in available:
        if in_my_size(category, lab, sizes, scale, dept):
            p = shoe(lab) if category == "footwear" else None
            if p and p[0] is None and scale == "eu":
                lab = f"EU {lab.split('/')[0].strip()}"
            out.append(lab.strip())
    return out

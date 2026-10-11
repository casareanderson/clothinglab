"""What kind of thing is this product? Category, garment type (for budget caps), colour family, fit words."""
from __future__ import annotations

import re

NOT_ADULT_MENS = re.compile(
    r"\b(women'?s?|womens|ladies|girls?|boys?|kids?|junior|infants?|toddlers?|baby|child(?:ren)?|youth|"
    r"\(gs\)|maternity|bra|bikini|dress|skirt)\b", re.I)
NON_FASHION = re.compile(
    r"\b(jewell?ery|necklace|earrings?|bracelet|perfume|fragrance|aftershave|candle|mug|book|poster|phone|"
    r"headphones?|toy|console|gift card|sticker)\b", re.I)

# Order matters: the first pattern that matches the TITLE wins (a "denim jacket" is outerwear, not a bottom).
CATS = [
    ("set", r"tracksuit|track ?suit|jogger set|matching set|two[- ]piece|co-?ord"),
    ("footwear", r"trainers?|sneakers?|shoes?|boots?|loafers?|runners?|mules?|slides?|sandals?|derby|brogues?|footwear"),
    ("outer", r"jackets?|coats?|parkas?|puffers?|gilets?|blazers?|harrington|bomber|anorak|windbreaker|overcoat|fleece"),
    ("bottom", r"jeans?|trousers?|chinos?|joggers?|track ?pants?|sweat ?pants?|pants|shorts|cargos?|slacks"),
    ("top", r"t-?shirts?|\btees?\b|shirts?|hoodies?|hooded|sweatshirts?|crew ?neck|jumpers?|sweaters?|knit(?:wear)?|"
            r"cardigans?|polos?|overshirts?|quarter[- ]zip|zip[- ]up|long ?sleeve|henley|rugby"),
    ("accessory", r"\bcaps?\b|\bhats?\b|beanies?|scarf|scarves|gloves|belts?|socks|bags?|backpacks?|totes?|wallets?"),
]
_CAT_RES = [(c, re.compile(r"\b(?:" + p + r")\b", re.I)) for c, p in CATS]

# Garment type -> the budget cap row it uses (tiers.py). Checked in order against title + product type.
GARMENTS = [
    ("trainers", r"trainers?|sneakers?|runners?|shoes?|boots?"),
    ("denim", r"jeans?|denim"),
    ("track", r"track ?(?:pants?|top|jacket)|joggers?|sweat ?pants?"),
    ("jacket", r"jackets?|coats?|parkas?|puffers?|gilets?|blazers?|bomber|harrington|overcoat|anorak|fleece"),
    ("hoodie", r"hoodies?|hooded|sweatshirts?|crew ?neck"),
    ("knit", r"knit(?:wear)?|jumpers?|sweaters?|cardigans?"),
    ("shirt", r"overshirts?|\bshirts?\b|polos?"),
    ("tee", r"t-?shirts?|\btees?\b|long ?sleeve|henley"),
    ("trousers", r"trousers?|chinos?|pants|cargos?|slacks|shorts"),
]
_GARMENT_RES = [(g, re.compile(r"\b(?:" + p + r")\b", re.I)) for g, p in GARMENTS]

COLOUR_FAMILIES = {
    "black": "black jet onyx anthracite",
    "white": "white off-white ecru cream ivory chalk",
    "grey": "grey gray charcoal heather silver",
    "neutral": "stone sand beige tan khaki oat taupe camel natural",
    "blue": "blue navy indigo denim cobalt royal midnight ink petrol teal",
    "green": "green olive forest sage bottle emerald moss army military pine hunter",
    "brown": "brown chocolate mocha coffee rust tobacco",
    "red": "red burgundy maroon wine oxblood",
    "pink": "pink rose blush fuchsia",
    "orange": "orange coral peach",
    "yellow": "yellow mustard lemon",
    "purple": "purple lilac lavender violet plum",
}
_COLOUR_RES = [(fam, re.compile(r"\b(?:" + "|".join(map(re.escape, words.split())) + r")\b", re.I))
               for fam, words in COLOUR_FAMILIES.items()]
NEUTRAL_FAMILIES = {"black", "white", "grey", "neutral"}


def category(title: str, product_type: str = "", tags: str = "") -> str | None:
    """'top' | 'outer' | 'bottom' | 'footwear' | 'set' | 'accessory' | None. Adult menswear only."""
    if NOT_ADULT_MENS.search(f"{title} {product_type}") or NON_FASHION.search(title):
        return None
    for c, rx in _CAT_RES:
        if rx.search(title):
            return c
    for c, rx in _CAT_RES:
        if rx.search(f"{product_type} {tags}"):
            return c
    return None


def garment(title: str, product_type: str = "") -> str:
    blob = f"{title} {product_type}"
    for g, rx in _GARMENT_RES:
        if rx.search(blob):
            return g
    return "other"


def colour_families(text: str) -> list[str]:
    return [fam for fam, rx in _COLOUR_RES if rx.search(text or "")]


def words(text: str, terms) -> list[str]:
    """Which of the profile's terms (e.g. fit words) appear in the text, as whole words."""
    hits = []
    for t in terms or []:
        t = str(t).strip()
        if t and re.search(r"\b" + re.escape(t) + r"\b", text or "", re.I):
            hits.append(t)
    return hits

import pytest

from clothinglab import catalog, engine, looks, onboard
from clothinglab import sizes as S
from clothinglab.fetch import Fetcher
from clothinglab.sources import shopify
from conftest import ALEX

W = {"tops": ["S", "M"], "dress_uk": [10, 12], "waist": [28], "trouser_length": "regular", "shoes_uk": [5, 5.5]}


@pytest.mark.parametrize("label,ok", [
    ("UK 10", True), ("10", True), ("12", True), ("14", False), ("S/10", True), ("XS/6", False), ("L/12", True),
    ("EU 38", True), ("EU 40", True), ("38", True), ("EU 42", False), ("US 6", True), ("US 10", False),
    ("8-10", True), ("UK 12-14", True), ("14-16", False), ("M", True), ("Medium", True), ("XL", False),
    ("10 Petite", False), ("10 Regular", True), ("Petite / 10", False),
])
def test_womens_clothing_labels(label, ok):
    assert S.in_my_size("dress", label, W, dept="womens") is ok


def test_petite_when_asked():
    assert S.in_my_size("dress", "10 Petite", {**W, "ranges": ["petite"]}, dept="womens")


@pytest.mark.parametrize("label,ok", [
    ("W28 L30", True),            # 30" leg is regular on women's jeans
    ("W28 L32", False),           # long
    ("W28 L28", False),           # short
    ("28", True), ("W28", True), ("10", True), ("10R", True), ("10S", False), ("12L", False),
    ("24", False),                # a women's 24 is a dress size, not a 24" waist
    ("S", True), ("L", False),
])
def test_womens_bottoms(label, ok):
    assert S.in_my_size("bottom", label, W, dept="womens") is ok


def test_mens_leg_is_different():
    assert S.waist("W32 L30", "mens") == (32, "short")
    assert S.waist("W28 L30", "womens") == (28, "regular")


@pytest.mark.parametrize("label,scale,ok", [
    ("5", "uk", True), ("UK 5.5", "uk", True), ("6", "uk", False),
    ("38", "eu", True), ("37.5", "eu", True), ("38.5", "eu", True), ("39", "eu", False),
    ("US 7", "uk", True), ("US 7.5", "uk", True), ("US 8", "uk", False), ("4Y", "uk", False),
])
def test_womens_shoes(label, scale, ok):
    assert S.in_my_size("footwear", label, W, scale=scale, dept="womens") is ok


def test_eu_detection_works_for_womens_ranges():
    assert S.shoe_scale(["36", "37", "38"]) == "eu"          # a men's-only '39+' rule would call this UK
    assert S.shoe_scale(["3", "4", "5", "6"]) == "uk"


def test_departments():
    assert catalog.department("Wrap Dress", "Womens Dresses") == "womens"
    assert catalog.department("Loopback Hoodie", "Mens Hoodies") == "mens"
    assert catalog.department("Plain Tee", "Tops") is None
    assert catalog.department("Plain Tee", "", "", hint="womens") == "womens"
    assert catalog.category("Wrap Midi Dress") == "dress" and catalog.category("Pleated Skirt") == "skirt"
    assert catalog.category("Ballet Flats") == "footwear" and catalog.category("Linen Blouse") == "top"
    assert catalog.category("Girls Party Dress") is None and catalog.category("Kids Logo Tee") is None
    assert catalog.wanted(None, "womens") and catalog.wanted("womens", "womens") and not catalog.wanted("mens", "womens")
    assert catalog.wanted("mens", "both")


def by_title(items):
    return {i["title"]: i for i in items}


def test_alex_in_size(shop):
    items = shopify.fetch(Fetcher("t/1", delay=0, allow_private=True), {"name": "fake", "url": shop})
    mine = by_title(engine.in_size(items, ALEX))
    assert mine["Wrap Midi Dress - Green"]["my_sizes"] == ["10"]                 # 12 is sold out
    assert mine["Pleated Midi Skirt - Navy"]["my_sizes"] == ["UK 10", "UK 12"]
    assert mine["Relaxed Linen Blouse - White"]["my_sizes"] == ["S/8", "M/10", "M/12"]
    assert mine["Wide Leg Jeans - Indigo"]["my_sizes"] == ["W28 L30"]
    assert mine["Straight Jeans - Blue"]["my_sizes"] == ["12"]                   # 10 regular sold out, petite not asked for
    assert mine["Chelsea Boots - Black"]["my_sizes"] == ["EU 38"]
    assert mine["Ballet Flats - Cream"]["my_sizes"] == ["5"]
    assert "Wool Wrap Coat - Camel" in mine and "Leather Tote Bag - Black" in mine
    assert "Maternity Jersey Dress - Black" not in mine
    assert not any(i.get("department") == "mens" for i in mine.values())
    ranked = by_title(engine.rank(list(mine.values()), ALEX))
    assert "Bodycon Dress - Orange" not in ranked
    assert ranked["Wrap Midi Dress - Green"]["tier"] == "mid" and ranked["Ballet Flats - Cream"]["tier"] == "low"


def test_alex_looks_dress_first(shop):
    items = shopify.fetch(Fetcher("t/1", delay=0, allow_private=True), {"name": "fake", "url": shop})
    ranked = engine.rank(engine.in_size(items, ALEX), ALEX)
    lks = {lk["tier"]: lk for lk in looks.build(ranked, ALEX)}
    cats = [p["category"] for p in lks["mid"]["pieces"]]
    assert cats[0] == "dress" and "footwear" in cats


def test_onboard_womens():
    prof, problems = onboard.build({"department": "womenswear please", "dress": "10 or 12", "tops": "S, M",
                                    "shoes": "5 or 5.5", "ranges": "petite", "fit_likes": "wide, midi",
                                    "palette": "green, navy", "caps": "dresses low under 30, boots high over 150"})
    assert problems == [], problems
    assert prof["department"] == "womens"
    assert prof["sizes"]["dress_uk"] == [10, 12] and prof["sizes"]["ranges"] == ["petite"]
    assert prof["budget"]["caps"] == {"dress": {"low": 30.0}, "boots": {"high": 150.0}}
    qs = [q["id"] for sec in onboard.questions("womens") for q in sec["questions"]]
    assert "dress" in qs and "ranges" in qs and "chart" not in qs
    assert "dress" not in [q["id"] for sec in onboard.questions("mens") for q in sec["questions"]]


def test_onboard_department_is_required_shape():
    _, problems = onboard.build({"department": "womens", "shoes": "5", "fit_likes": "wide", "palette": "green"})
    assert any("dress" in p for p in problems)

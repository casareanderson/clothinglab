from clothinglab import catalog, tiers


def test_category():
    assert catalog.category("Loopback Hoodie - Navy") == "top"
    assert catalog.category("Denim Trucker Jacket") == "outer"
    assert catalog.category("Straight Selvedge Jeans") == "bottom"
    assert catalog.category("Court Trainer") == "footwear"
    assert catalog.category("Kids Logo Tee") is None
    assert catalog.category("Womens Relaxed Tee") == "top"          # department is separate from category
    assert catalog.category("Scented Candle") is None
    assert catalog.category("Item 42", "Hoodies") == "top"


def test_garment_and_colour():
    assert catalog.garment("Boxy Pocket Tee") == "tee"
    assert catalog.garment("Selvedge Jeans") == "denim"
    assert catalog.garment("Court Trainer") == "trainers"
    assert catalog.colour_families("Navy / Olive") == ["blue", "green"]


def test_tiers_absolute():
    caps = tiers.caps({"tiers": {"caps": {"tee": {"low": 20}}}}, {"budget": {"caps": {"hoodie": {"high": 60}}}})
    assert tiers.tier_for("tee", 18, caps) == "low"
    assert tiers.tier_for("tee", 22, caps) == "mid"           # config moved the low line to 20
    assert tiers.tier_for("hoodie", 61, caps) == "high"       # profile moved the high line to 60
    assert tiers.tier_for("mystery", 500, caps) == "high"     # falls back to 'other'
    assert tiers.tier_for("tee", None, caps) is None
    assert tiers.enabled({"budget": {"tiers": ["high", "low"]}}) == ["low", "high"]
    assert tiers.badge("low") == "💸 Low"

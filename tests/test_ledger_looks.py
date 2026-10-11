from datetime import datetime, timedelta, timezone

from clothinglab import looks
from clothinglab.ledger import Ledger, family_key
from conftest import SAM


def item(title, price=50.0, sizes=("L",), url=None, **kw):
    return {"id": title, "title": title, "price": price, "my_sizes": list(sizes), "url": url or f"https://s.invalid/{title}",
            "source": "s", **kw}


def test_colourways_are_one_family():
    a = item("Loopback Hoodie - Navy", url="https://s.invalid/a")
    b = item("Loopback Hoodie - Grey", url="https://s.invalid/b")
    assert family_key(a) == family_key(b)
    assert family_key(item("Loopback Hoodie Olive Green", url="https://s.invalid/c")) == family_key(a)


def test_no_repeat_then_worthwhile_reshow(tmp_path):
    L = Ledger(tmp_path / "shown.json")
    hoodie = item("Loopback Hoodie - Navy", 50)
    assert L.filter([hoodie]) == [hoodie]
    L.record([hoodie])
    L = Ledger(tmp_path / "shown.json")
    assert L.filter([hoodie]) == []                                   # shown: stays out
    assert L.filter([item("Loopback Hoodie - Grey", 50)]) == []      # other colourway: same family
    cheaper = L.filter([item("Loopback Hoodie - Navy", 47)])
    assert cheaper and cheaper[0]["reshow"].startswith("🔁 cheaper again")
    assert L.filter([item("Loopback Hoodie - Navy", 49)]) == []      # 2% isn't news


def test_back_in_size_and_expiry(tmp_path):
    L = Ledger(tmp_path / "shown.json")
    h = item("Court Trainer - White", 70, sizes=("9",))
    L.record([h])
    L.note_sold_out([h], [])                                          # still listed, gone from my size
    again = Ledger(tmp_path / "shown.json").filter([h])
    assert again and again[0]["reshow"] == "🔁 back in your size"
    k = family_key(h)
    L.rows[k]["sizes"] = ["9"]
    L.rows[k]["last"] = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
    assert L.filter([h]) == [h]                                       # 14 days on: fair game


def test_never_twice_in_one_digest(tmp_path):
    L = Ledger(tmp_path / "shown.json")
    assert len(L.filter([item("Tee - Navy"), item("Tee - Olive")])) == 1


def test_looks_one_per_tier():
    ranked = [
        {"id": "t1", "title": "Boxy Tee - Olive", "category": "top", "tier": "low", "price": 18, "colour": "olive"},
        {"id": "b1", "title": "Track Pant - Black", "category": "bottom", "tier": "low", "price": 30, "colour": "black"},
        {"id": "f1", "title": "Court Trainer - White", "category": "footwear", "tier": "low", "price": 60, "colour": "white"},
        {"id": "t2", "title": "Hoodie - Navy", "category": "top", "tier": "mid", "price": 48, "colour": "navy"},
        {"id": "b2", "title": "Jeans - Indigo", "category": "bottom", "tier": "mid", "price": 89, "colour": "indigo"},
        {"id": "t3", "title": "Knit - Pink", "category": "top", "tier": "high", "price": 140, "colour": "pink"},
    ]
    lks = {lk["tier"]: lk for lk in looks.build(ranked, SAM)}
    assert [p["id"] for p in lks["low"]["pieces"]] == ["t1", "b1", "f1"] and lks["low"]["total"] == 108
    mid = lks["mid"]["pieces"]                                        # no mid shoes: the owned trainers fill in
    assert mid[-1].get("owned") and lks["mid"]["total"] == 137
    assert lks["high"]["pieces"] == [] and "no full High look" in lks["high"]["note"]

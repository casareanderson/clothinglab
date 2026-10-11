import pytest

from clothinglab import engine
from clothinglab.fetch import FetchError, Fetcher, public_url
from clothinglab.sources import jsonld, shopify
from conftest import SAM


def F():
    return Fetcher("ClothingLab-tests/1.0", delay=0, allow_private=True)


def by_title(items):
    return {i["title"]: i for i in items}


def test_shopify_reads_sizes_and_prices(shop):
    items = shopify.fetch(F(), {"name": "fake", "url": shop})
    t = by_title(items)
    assert "Kids Logo Tee" not in t                                # not adult menswear
    h = t["Loopback Hoodie - Navy"]
    assert h["price"] == 48 and h["was"] == 85 and h["discount"] == pytest.approx(0.435, abs=0.001)
    assert "M" not in h["sizes_available"] and "L" in h["sizes_available"]
    assert t["Trail Runner - Olive"]["category"] == "footwear"


def test_in_size_and_rank(shop):
    items = shopify.fetch(F(), {"name": "fake", "url": shop})
    mine = by_title(engine.in_size(items, SAM))
    assert mine["Loopback Hoodie - Navy"]["my_sizes"] == ["L"]     # M sold out, L left
    assert "Chunky Knit Jumper - Green" not in mine                # M and L sold out
    assert mine["Trail Runner - Olive"]["my_sizes"] == ["EU 44", "EU 44.5"]
    assert mine["Straight Selvedge Jeans - Indigo"]["my_sizes"] == ["32R"]
    assert "Harrington Jacket - Navy" in mine
    ranked = by_title(engine.rank(list(mine.values()), SAM))
    assert "Skinny Stretch Jeans - Black" not in ranked            # fit.never
    assert "Heavyweight Tee - Pink" not in ranked                  # colours.avoid
    assert ranked["Loopback Hoodie - Navy"]["tier"] == "mid"
    assert ranked["Boxy Pocket Tee - Olive"]["tier"] == "low"
    assert "you like Northfold" in ranked["Loopback Hoodie - Navy"]["why"]


def test_jsonld_adapter(shop):
    items = jsonld.fetch(F(), {"name": "ld", "sitemap": f"{shop}/sitemap.xml", "product_url_pattern": "/p/"})
    t = by_title(items)
    assert t["Court Trainer - White"]["sizes_available"] == ["7", "8", "9", "9.5", "10", "11"]
    assert t["Loopback Hoodie - Navy"]["price"] == 48


def test_jsonld_single_offer_is_size_unknown():
    html = ('<script type="application/ld+json">{"@type":"Product","name":"Plain Tee","offers":'
            '{"@type":"Offer","price":"20","availability":"https://schema.org/InStock"}}</script>')
    it = jsonld.parse_page(html, "https://shop.invalid/p/plain-tee", {"name": "x"})
    assert it["sizes_available"] is None                           # never presented as in your size
    assert engine.in_size([it], SAM) == []


def test_robots_and_private_hosts(shop):
    f = F()
    with pytest.raises(FetchError, match="robots"):
        f.get(f"{shop}/private/thing")
    assert not public_url("http://127.0.0.1/x")
    assert not public_url("file:///etc/passwd")
    assert public_url("http://127.0.0.1/x", allow_private=True)
    with pytest.raises(FetchError, match="non-public"):
        Fetcher("ua/1", delay=0).get(f"{shop}/products.json")
    with pytest.raises(FetchError, match="user_agent"):
        Fetcher("ClothingLab/0.1 (CHANGE-ME)")


def test_gather_reports_failures(shop):
    cfg = {"user_agent": "t/1", "politeness": {"delay_seconds": 0, "allow_private_hosts": True},
           "sources": [{"name": "ok", "url": shop}, {"name": "dead", "url": "http://127.0.0.1:9"}]}
    items, health = engine.gather(cfg, log=lambda *a: None)
    assert health["ok"]["ok"] and not health["dead"]["ok"] and items

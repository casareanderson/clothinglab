import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))
import fake_shop  # noqa: E402

SAM = {
    "schema_version": 1, "name": "Sam",
    "sizes": {"tops": ["M", "L"], "waist": [32], "trouser_length": "regular", "bottoms_letter": ["M"], "shoes_uk": [9, 9.5]},
    "fit": {"likes": ["relaxed", "straight", "boxy"], "never": ["skinny"]},
    "colours": {"palette": ["navy", "olive"], "avoid": ["pink"]},
    "brands": {"love": ["Northfold"], "never": []},
    "budget": {"tiers": ["low", "mid", "high"]},
    "wardrobe": [{"name": "white leather trainers", "category": "footwear", "colour": "white"}],
}


@pytest.fixture()
def shop():
    srv, url = fake_shop.start()
    yield url
    srv.shutdown()


@pytest.fixture()
def home(tmp_path, monkeypatch, shop):
    monkeypatch.setenv("CLOTHINGLAB_HOME", str(tmp_path))
    cfg = {"user_agent": "ClothingLab-tests/1.0 (pytest)",
           "politeness": {"delay_seconds": 0, "allow_private_hosts": True},
           "sources": [{"name": "fake", "adapter": "shopify", "url": shop}]}
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(cfg))
    (tmp_path / "profile.yaml").write_text(yaml.safe_dump(SAM))
    return tmp_path

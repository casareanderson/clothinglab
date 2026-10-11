import asyncio
import json
from pathlib import Path

import fake_shop
import pytest
import yaml

from clothinglab import app, cli, mcp_server, onboard, store, watch

EXAMPLES = Path(__file__).parent.parent / "clothinglab" / "examples"


def test_onboard_from_answers():
    answers = json.loads((EXAMPLES / "answers.example.json").read_text())
    prof, problems = onboard.build(answers)
    assert problems == []
    assert prof["sizes"] == {"tops": ["M", "L"], "waist": [32], "trouser_length": "regular", "bottoms_letter": ["M"],
                             "shoes_uk": [9.0, 9.5]}
    assert prof["budget"]["caps"] == {"tee": {"low": 20.0}}
    assert prof["wardrobe"][0]["category"] == "footwear"


def test_onboard_missing_and_forbidden():
    prof, problems = onboard.build({"department": "mens", "tops": "M"})
    assert any("waist" in p for p in problems) and any("shoes" in p for p in problems)
    assert onboard.validate({"sizes": {"tops": ["M"], "waist": [32], "shoes_uk": [9]}, "height": 180}) == \
        ["profile must not store height"]
    assert any("department" in p for p in onboard.build({"tops": "M", "waist": "32", "shoes": "9"})[1])


def test_full_flow(home):
    s = app.refresh(log=lambda *a: None)
    assert s["seen"] > 10 and s["in_size"] >= 8
    t = app.todays(6, mark_shown=True)
    tiers_seen = [p["tier"] for p in t["picks"][:3]]
    assert set(tiers_seen) == {"low", "mid", "high"}                 # one per tier first
    again = app.todays(6)
    shown = {p["id"] for p in t["picks"]}
    assert not shown & {p["id"] for p in again["picks"]}             # nothing repeats
    md = app.digest_markdown(check_watch=False)
    assert "# ClothingLab for Sam" in md and "Looks" in md
    assert [r["title"] for r in app.search(category="footwear")] == ["Trail Runner - Olive", "Court Trainer - White"] or \
        {r["title"] for r in app.search(category="footwear")} == {"Trail Runner - Olive", "Court Trainer - White"}


def test_watch_price_drop(home, shop):
    url = f"{shop}/products/court-trainer-white"
    watch.add(url, target=70)
    f = app.engine.fetcher_from(store.config())
    assert watch.check(f, store.profile()) == []                     # first read just records 74
    p = next(x for x in fake_shop.PRODUCTS if x["handle"] == "court-trainer-white")
    old = [v["price"] for v in p["variants"]]
    try:
        for v in p["variants"]:
            v["price"] = "69.00"
        alerts = watch.check(f, store.profile())
    finally:
        for v, o in zip(p["variants"], old):
            v["price"] = o
    assert alerts and alerts[0]["old"] == 74 and alerts[0]["new"] == 69 and "9" in alerts[0]["my_sizes"]


def test_cli(home, capsys, tmp_path):
    assert cli.main(["refresh"]) == 0
    assert "in stock in your size" in capsys.readouterr().out
    out = tmp_path / "d.html"
    assert cli.main(["digest", "--no-watch", "--format", "html", "--out", str(out)]) == 0
    assert "<h1>ClothingLab for Sam" in out.read_text()
    assert cli.main(["validate"]) == 0


def test_cli_init_and_onboard(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOTHINGLAB_HOME", str(tmp_path))
    assert cli.main(["init"]) == 0
    assert (tmp_path / "config.yaml").exists() and (tmp_path / "profile.yaml").exists()
    assert cli.main(["onboard", "--answers", str(EXAMPLES / "answers.example.json")]) == 0
    assert (tmp_path / "profile.new.yaml").exists()                  # never clobbers without --force


def test_not_set_up(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOTHINGLAB_HOME", str(tmp_path))
    assert cli.main(["picks"]) == 2


def test_mcp_tools(home):
    names = [t.name for t, _ in mcp_server.TOOLS]
    assert names[0] == "clothinglab_questions" and "clothinglab_todays_picks" in names
    server = mcp_server.build_server()
    handlers = {t.name: fn for t, fn in mcp_server.TOOLS}
    q = json.loads(handlers["clothinglab_questions"]({})[0].text)
    assert q["sections"][0]["id"] == "department"
    w = json.loads(handlers["clothinglab_questions"]({"department": "womens"})[0].text)
    assert "dress" in [x["id"] for sec in w["sections"] for x in sec["questions"]]
    app.refresh(log=lambda *a: None)
    res = json.loads(handlers["clothinglab_search"]({"category": "top", "tier": "low"})[0].text)
    assert res and all(r["tier"] == "low" for r in res)
    res = json.loads(handlers["clothinglab_save_profile"]({"answers": {"tops": "M"}})[0].text)
    assert res["saved"] is False and res["problems"]
    assert server.name == "clothinglab"


def test_sources_local_merges(home):
    (home / "sources.local.yaml").write_text(yaml.safe_dump([{"name": "fake", "url": "http://127.0.0.1:1"},
                                                            {"name": "extra", "url": "http://127.0.0.1:2"}]))
    srcs = {s["name"]: s["url"] for s in store.config()["sources"]}
    assert srcs == {"fake": "http://127.0.0.1:1", "extra": "http://127.0.0.1:2"}   # local wins on the same name


def test_dry_run_records_nothing(home, capsys):
    app.refresh(log=lambda *a: None)
    assert cli.main(["digest", "--dry-run", "--no-watch", "--mark-shown", "--discord"]) == 0
    assert "Top picks" in capsys.readouterr().out
    assert not (home / "data" / "shown.json").exists()

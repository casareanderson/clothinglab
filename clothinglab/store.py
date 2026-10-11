"""Where ClothingLab keeps things. One folder, $CLOTHINGLAB_HOME (default ~/.clothinglab):

  profile.yaml   who you are: sizes, fit, colours, brands, budget (written by the onboarding interview)
  config.yaml    where to look: sources, politeness, tier caps, delivery
  sources.local.yaml    optional: extra shops, merged into config.yaml's sources
  data/pool.json        the latest products seen, in your size or not
  data/shown.json       what you've already been shown (the no-repeat ledger)
  data/watch.json       your watchlist
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml


def home() -> Path:
    return Path(os.environ.get("CLOTHINGLAB_HOME", Path.home() / ".clothinglab")).expanduser()


def data_dir() -> Path:
    d = home() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_yaml(p: Path, default=None):
    p = Path(p)
    if not p.exists():
        return {} if default is None else default
    return yaml.safe_load(p.read_text(encoding="utf-8")) or ({} if default is None else default)


def load_json(p: Path, default):
    p = Path(p)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return default


def save_json(p: Path, obj) -> None:
    """Atomic write, owner-only: these files say what you wear and buy."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=p.name + ".")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def profile() -> dict:
    return load_yaml(home() / "profile.yaml")


def config() -> dict:
    """config.yaml, plus any shops in sources.local.yaml (a plain list, or {sources: [...]}) so you can add shops
    without touching the main file. A local source with the same name replaces the one in config.yaml."""
    cfg = load_yaml(home() / "config.yaml")
    local = load_yaml(home() / "sources.local.yaml", default=[])
    extra = local.get("sources", []) if isinstance(local, dict) else (local or [])
    if extra:
        names = {s.get("name") for s in extra}
        cfg["sources"] = [s for s in cfg.get("sources") or [] if s.get("name") not in names] + list(extra)
    return cfg


def pool() -> list[dict]:
    return load_json(data_dir() / "pool.json", {"items": []}).get("items", [])


def save_pool(items: list[dict], meta: dict | None = None) -> None:
    save_json(data_dir() / "pool.json", {"updated": now_iso(), **(meta or {}), "items": items})

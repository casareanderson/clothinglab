"""The few operations everything else (CLI, MCP server, your own scripts) calls."""
from __future__ import annotations

from . import catalog, digest, engine, looks as L, store, tiers, watch
from .ledger import Ledger


class NotSetUp(RuntimeError):
    pass


def _need():
    prof, cfg = store.profile(), store.config()
    if not prof:
        raise NotSetUp(f"no profile at {store.home() / 'profile.yaml'}: run `clothinglab onboard` first")
    return prof, cfg


def refresh(fetcher=None, log=print) -> dict:
    """Fetch every source, keep the whole pool (so 'back in your size' can be noticed). -> health summary."""
    prof, cfg = _need()
    items, health = engine.gather(cfg, fetcher, log=log)
    store.save_pool(items, {"health": health})
    mine = engine.in_size(items, prof)
    Ledger().note_sold_out(items, mine)
    return {"seen": len(items), "in_size": len(mine), "sources": health}


def ranked(include_shown: bool = True) -> list[dict]:
    prof, cfg = _need()
    items = store.pool()
    sale_only = (cfg.get("digest") or {}).get("sale_only", True)
    out = engine.rank(engine.in_size(items, prof), prof, tiers.caps(cfg, prof), sale_only=sale_only)
    return out if include_shown else Ledger().filter(out)


def search(category: str | None = None, tier: str | None = None, max_price: float | None = None,
           query: str | None = None, limit: int = 20) -> list[dict]:
    out = []
    for it in ranked():
        if category and it["category"] != category:
            continue
        if tier and it.get("tier") != tier:
            continue
        if max_price is not None and (it.get("price") is None or it["price"] > max_price):
            continue
        if query and not catalog.words(f"{it.get('brand', '')} {it['title']} {it.get('colour', '')}", query.split()):
            continue
        out.append(it)
        if len(out) >= limit:
            break
    return out


def todays(n: int = 6, mark_shown: bool = False) -> dict:
    """The digest's content: picks (one per tier first) + looks, from items you haven't been shown."""
    prof, _ = _need()
    pool_all = store.pool()
    fresh = ranked(include_shown=False)
    top = digest.picks(fresh, prof, n)
    lks = L.build([x for x in fresh if x["id"] not in {t["id"] for t in top}] + top, prof)
    if mark_shown:
        shown = top + [p for lk in lks for p in lk["pieces"] if not p.get("owned")]
        Ledger().record(shown)
    return {"picks": top, "looks": lks,
            "stats": {"seen": len(pool_all), "in_size": len(engine.in_size(pool_all, prof)), "match": len(ranked()),
                      "new": len(fresh)}}


def digest_markdown(mark_shown: bool = False, fetcher=None, check_watch: bool = True) -> str:
    prof, cfg = _need()
    t = todays(int((cfg.get("digest") or {}).get("picks", 6)), mark_shown)
    alerts = watch.check(fetcher or engine.fetcher_from(cfg), prof) if check_watch and watch.load() else []
    return digest.render(t["picks"], t["looks"], alerts, prof.get("name", ""), t["stats"])


def brief(it: dict) -> dict:
    """What an AI assistant needs about one item, without the noise."""
    keys = ("title", "brand", "price", "was", "currency", "tier", "my_sizes", "category", "url", "why", "reshow", "image")
    return {k: it.get(k) for k in keys if it.get(k) not in (None, [], "")}

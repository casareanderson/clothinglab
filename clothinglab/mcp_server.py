"""ClothingLab as an MCP server (stdio), so any MCP client can use it: Claude Desktop / Claude Code, Cursor,
ChatGPT connectors, Grok through xAI's remote-MCP bridge, Hermes, and others.

Tools never post anywhere and never buy anything. `refresh` is the only one that goes to the internet for the pool;
`watch_check` reads the watched product pages.
"""
from __future__ import annotations

import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import app, onboard, store, watch, engine

_EMPTY = {"type": "object", "properties": {}}


def _text(obj) -> list[TextContent]:
    return [TextContent(type="text", text=obj if isinstance(obj, str) else json.dumps(obj, indent=1, ensure_ascii=False))]


def t_questions(a):
    dept = a.get("department")
    return _text({"sections": onboard.questions(dept),
                  "how": "Ask the department question first (menswear, womenswear or both), then call this tool again "
                         "with that department to get only the questions that apply. Ask section by section, in your "
                         "own words. Then call clothinglab_save_profile with {question_id: the person's answer}. "
                         "Never ask for height, weight or body measurements."})


def t_save_profile(a):
    prof, problems = onboard.build(a.get("answers") or {})
    if problems and not a.get("save_anyway"):
        return _text({"saved": False, "problems": problems, "profile_preview": prof})
    path = store.home() / "profile.yaml"
    if path.exists() and not a.get("overwrite"):
        return _text({"saved": False, "problems": [f"{path} exists; pass overwrite=true to replace it"]})
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(prof, sort_keys=False, allow_unicode=True), encoding="utf-8")
    path.chmod(0o600)
    return _text({"saved": True, "path": str(path), "problems": problems})


def t_profile(a):
    return _text(store.profile() or {"error": "no profile yet; use clothinglab_questions"})


def t_refresh(a):
    return _text(app.refresh(log=lambda *x: None))


def t_search(a):
    rows = app.search(a.get("category"), a.get("tier"), a.get("max_price"), a.get("query"), int(a.get("limit", 15)))
    return _text([app.brief(r) for r in rows])


def t_todays(a):
    t = app.todays(int(a.get("limit", 6)), bool(a.get("mark_shown", False)))
    return _text({"picks": [app.brief(p) for p in t["picks"]], "stats": t["stats"],
                  "looks": [{"tier": lk["tier"], "total": lk["total"], "note": lk["note"],
                             "pieces": [app.brief(p) | ({"owned": True} if p.get("owned") else {}) for p in lk["pieces"]]}
                            for lk in t["looks"]]})


def t_digest(a):
    return _text(app.digest_markdown(mark_shown=bool(a.get("mark_shown", False)), check_watch=False))


def t_watch_add(a):
    return _text(watch.add(a["url"], a.get("target_price"), a.get("note", "")))


def t_watch_list(a):
    return _text(watch.load())


def t_watch_check(a):
    return _text(watch.check(engine.fetcher_from(store.config()), store.profile()))


TOOLS = [
    (Tool(name="clothinglab_questions",
          description="The onboarding interview (department, sizes, fit, colours, brands, budget tiers, wardrobe). Start here for a new person.",
          inputSchema={"type": "object", "properties": {
              "department": {"type": "string", "enum": ["mens", "womens", "both"],
                             "description": "once known: only the questions for that department"}}}),
     t_questions),
    (Tool(name="clothinglab_save_profile", description="Turn interview answers into the person's profile.yaml.",
          inputSchema={"type": "object", "required": ["answers"], "properties": {
              "answers": {"type": "object", "description": "{question_id: answer in the person's words}"},
              "overwrite": {"type": "boolean"}, "save_anyway": {"type": "boolean"}}}), t_save_profile),
    (Tool(name="clothinglab_profile", inputSchema=_EMPTY, description="Show the saved profile."), t_profile),
    (Tool(name="clothinglab_refresh", inputSchema=_EMPTY,
          description="Fetch every configured shop (slow, polite). Run once a day, not per question."), t_refresh),
    (Tool(name="clothinglab_search", description="In-stock items in the person's size from the last refresh, ranked.",
          inputSchema={"type": "object", "properties": {
              "category": {"type": "string", "enum": ["top", "outer", "bottom", "footwear", "set", "accessory"]},
              "tier": {"type": "string", "enum": ["low", "mid", "high"]},
              "max_price": {"type": "number"}, "query": {"type": "string", "description": "words, e.g. 'navy hoodie'"},
              "limit": {"type": "integer"}}}), t_search),
    (Tool(name="clothinglab_todays_picks", description="Today's picks (one per budget tier first) and looks, skipping things already shown.",
          inputSchema={"type": "object", "properties": {"limit": {"type": "integer"},
                                                         "mark_shown": {"type": "boolean", "description": "record them so they don't repeat"}}}),
     t_todays),
    (Tool(name="clothinglab_digest", description="The full digest as Markdown.",
          inputSchema={"type": "object", "properties": {"mark_shown": {"type": "boolean"}}}), t_digest),
    (Tool(name="clothinglab_watch_add", description="Watch a product URL for a price drop or a target price.",
          inputSchema={"type": "object", "required": ["url"], "properties": {
              "url": {"type": "string"}, "target_price": {"type": "number"}, "note": {"type": "string"}}}), t_watch_add),
    (Tool(name="clothinglab_watch_list", inputSchema=_EMPTY, description="The watchlist."), t_watch_list),
    (Tool(name="clothinglab_watch_check", inputSchema=_EMPTY, description="Re-check watched products now."), t_watch_check),
]


def build_server() -> Server:
    server = Server("clothinglab")
    handlers = {t.name: fn for t, fn in TOOLS}

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [t for t, _ in TOOLS]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        fn = handlers.get(name)
        if not fn:
            return _text({"error": f"unknown tool {name}"})
        try:
            return await asyncio.to_thread(fn, arguments or {})
        except app.NotSetUp as e:
            return _text({"error": str(e), "next": "clothinglab_questions"})
        except Exception as e:      # an MCP client should get a message, not a dropped session
            return _text({"error": f"{type(e).__name__}: {e}"})

    return server


async def serve() -> None:
    server = build_server()
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> int:
    asyncio.run(serve())
    return 0

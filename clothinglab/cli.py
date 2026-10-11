"""clothinglab: deals in your size, from shops you choose.

  clothinglab init                 copy the example config + profile into $CLOTHINGLAB_HOME
  clothinglab onboard              the interview in the terminal -> profile.yaml
  clothinglab onboard --answers answers.json [--force]
  clothinglab validate             check profile.yaml
  clothinglab refresh              fetch every source (slow and polite)
  clothinglab picks [-n 6]         today's picks, not yet shown
  clothinglab search [--category top] [--tier low] [--max-price 40] [--query "navy"]
  clothinglab looks                one look per budget tier
  clothinglab digest [--mark-shown] [--out FILE] [--discord] [--email ADDRESS] [--format md|text|html]
  clothinglab watch add URL [--target 60] | list | remove URL | check
  clothinglab mcp                  run the MCP server on stdio
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from importlib import resources
from pathlib import Path

import yaml

from . import app, deliver, digest as D, engine, onboard, store, tiers, watch
from .fetch import FetchError


def _examples() -> Path:
    return Path(str(resources.files("clothinglab") / "examples"))


def cmd_init(a):
    h = store.home()
    h.mkdir(parents=True, exist_ok=True)
    for name in ("config.example.yaml", "profile.example.yaml"):
        dst = h / name.replace(".example", "")
        if dst.exists() and not a.force:
            print(f"keep  {dst}")
            continue
        shutil.copy(_examples() / name, dst)
        dst.chmod(0o600)
        print(f"wrote {dst}")
    print("next: edit config.yaml (set user_agent, pick sources), then `clothinglab onboard`")


def cmd_onboard(a):
    if a.answers:
        answers = json.loads(Path(a.answers).read_text())
    else:
        answers = {}
        for sec in onboard.questions():
            print(f"\n== {sec['title']} ==" + (f"\n{sec['intro']}" if sec["intro"] else ""))
            for q in sec["questions"]:
                v = input(q["ask"] + (" *" if q.get("required") else "") + "\n> ").strip()
                if v:
                    answers[q["id"]] = v
    prof, problems = onboard.build(answers)
    for p in problems:
        print("problem:", p)
    path = store.home() / "profile.yaml"
    if path.exists() and not a.force:
        path = store.home() / "profile.new.yaml"
        print(f"profile.yaml exists; writing {path} (use --force to replace)")
    elif path.exists():
        shutil.copy(path, path.with_suffix(".yaml.bak"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(prof, sort_keys=False, allow_unicode=True), encoding="utf-8")
    path.chmod(0o600)
    print(f"saved {path}")
    return 1 if problems else 0


def cmd_validate(a):
    problems = onboard.validate(store.profile())
    print("\n".join(problems) or "profile OK")
    return 1 if problems else 0


def cmd_refresh(a):
    s = app.refresh()
    for name, h in s["sources"].items():
        print(f"  {name:28} {'ok ' + str(h['items']) + ' products' if h['ok'] else 'FAILED ' + h['error']}")
    print(f"{s['seen']} products checked, {s['in_size']} in stock in your size")


def _print_items(rows):
    for r in rows:
        print(D.to_text(D.line(r)))


def cmd_picks(a):
    t = app.todays(a.n, mark_shown=False)
    _print_items(t["picks"]) if t["picks"] else print("nothing new in your size")


def cmd_search(a):
    _print_items(app.search(a.category, a.tier, a.max_price, a.query, a.limit))


def cmd_looks(a):
    for lk in app.todays()["looks"]:
        head = tiers.badge(lk["tier"])
        if not lk["pieces"]:
            print(f"{head}: {lk['note']}")
        else:
            print(f"{head} · {D.money(lk['total'])}: " + " + ".join(("yours: " if p.get("owned") else "") + p["title"] for p in lk["pieces"]))


def cmd_digest(a):
    md = app.digest_markdown(mark_shown=a.mark_shown, check_watch=not a.no_watch)
    out = {"md": md, "text": D.to_text(md), "html": D.to_html(md)}[a.format]
    if a.out:
        deliver.to_file(out, a.out)
        print("wrote", a.out)
    if a.discord:
        print("discord chunks:", deliver.discord_webhook(md))
    if a.email:
        deliver.email(md, a.email)
        print("emailed", a.email)
    if not (a.out or a.discord or a.email):
        print(out)


def cmd_watch(a):
    if a.action == "add":
        print(json.dumps(watch.add(a.url, a.target), indent=1))
    elif a.action == "remove":
        print("removed" if watch.remove(a.url) else "not on the list")
    elif a.action == "check":
        alerts = watch.check(engine.fetcher_from(store.config()), store.profile())
        print(json.dumps(alerts, indent=1, ensure_ascii=False) if alerts else "no drops")
    else:
        for r in watch.load():
            print(f"{D.money(r.get('price'))} target {D.money(r.get('target')) if r.get('target') else '-'}  {r.get('title') or ''}  {r['url']}")


def cmd_mcp(a):
    from .mcp_server import main
    return main()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="clothinglab", description="Deals in your size, from shops you choose.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("onboard"); p.add_argument("--answers"); p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_onboard)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    sub.add_parser("refresh").set_defaults(fn=cmd_refresh)
    p = sub.add_parser("picks"); p.add_argument("-n", type=int, default=6); p.set_defaults(fn=cmd_picks)
    p = sub.add_parser("search")
    p.add_argument("--category"); p.add_argument("--tier", choices=tiers.TIERS); p.add_argument("--max-price", type=float)
    p.add_argument("--query"); p.add_argument("--limit", type=int, default=20); p.set_defaults(fn=cmd_search)
    sub.add_parser("looks").set_defaults(fn=cmd_looks)
    p = sub.add_parser("digest")
    p.add_argument("--mark-shown", action="store_true", help="record what was shown so it won't repeat")
    p.add_argument("--no-watch", action="store_true"); p.add_argument("--out"); p.add_argument("--discord", action="store_true")
    p.add_argument("--email"); p.add_argument("--format", choices=["md", "text", "html"], default="md"); p.set_defaults(fn=cmd_digest)
    p = sub.add_parser("watch"); p.add_argument("action", choices=["add", "list", "remove", "check"])
    p.add_argument("url", nargs="?"); p.add_argument("--target", type=float); p.set_defaults(fn=cmd_watch)
    sub.add_parser("mcp").set_defaults(fn=cmd_mcp)
    a = ap.parse_args(argv)
    if a.cmd == "watch" and a.action in ("add", "remove") and not a.url:
        ap.error("watch add/remove needs a URL")
    try:
        return a.fn(a) or 0
    except (app.NotSetUp, FetchError) as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

"""Turn ranked items + looks into one readable digest (Markdown; plain text and HTML are derived from it)."""
from __future__ import annotations

import html
import re
from datetime import date

from . import tiers

SYMBOL = {"GBP": "£", "EUR": "€", "USD": "$"}


def money(x, currency="GBP") -> str:
    if x is None:
        return "?"
    s = SYMBOL.get(currency, currency + " ")
    return f"{s}{x:,.0f}" if float(x).is_integer() else f"{s}{x:,.2f}"


def line(it: dict) -> str:
    cur = it.get("currency", "GBP")
    price = money(it.get("price"), cur)
    if it.get("was"):
        price += f" ~~{money(it['was'], cur)}~~"
    extras = []
    if it.get("tier"):
        extras.append(tiers.badge(it["tier"]))
    if it.get("my_sizes"):
        extras.append("your size: " + ", ".join(it["my_sizes"][:3]))
    if it.get("reshow"):
        extras.append(it["reshow"])
    if it.get("why"):
        extras.append(", ".join(it["why"][:3]))
    head = f"- **{it.get('brand', '')}** {it['title']} · {price}"
    return head + ("".join(f" · {e}" for e in extras)) + f"  \n  <{it['url']}>"


def picks(ranked: list[dict], profile: dict, n: int = 6) -> list[dict]:
    """One per enabled tier first (where stock allows), then the best of the rest."""
    out, used = [], set()
    for t in tiers.enabled(profile):
        it = next((x for x in ranked if x.get("tier") == t and x["id"] not in used), None)
        if it:
            out.append(it)
            used.add(it["id"])
    for it in ranked:
        if len(out) >= n:
            break
        if it["id"] not in used:
            out.append(it)
            used.add(it["id"])
    return out[:n]


def render(top: list[dict], looks: list[dict], watch_alerts: list[dict] | None = None, name: str = "",
           stats: dict | None = None) -> str:
    who = f" for {name}" if name else ""
    md = [f"# ClothingLab{who} · {date.today():%a %d %b}", ""]
    if stats:
        md.append(f"_{stats.get('seen', 0)} products checked · {stats.get('in_size', 0)} in stock in your size · "
                  f"{stats.get('match', 0)} match your profile · {stats.get('new', 0)} you haven't seen_")
        md.append("")
    if watch_alerts:
        md.append("## 👀 Watchlist")
        for a in watch_alerts:
            old = f"{money(a['old'])} → " if a.get("old") is not None else ""
            md.append(f"- **{a['title']}** {old}{money(a['new'])}" + (f" (target {money(a['target'])})" if a.get("target") else "")
                      + f"  \n  <{a['url']}>")
        md.append("")
    md.append("## 🔥 Top picks in your size")
    md.extend(line(it) for it in top) if top else md.append("_Nothing new in your size today. That's fine._")
    md.append("")
    if looks:
        md.append("## 👔 Looks")
        for lk in looks:
            head = f"**{tiers.badge(lk['tier'])}**"
            if not lk["pieces"]:
                md.append(f"- {head}: {lk['note']}")
                continue
            parts = [("yours: " if p.get("owned") else "") + p["title"] + ("" if p.get("owned") else f" ({money(p.get('price'))})")
                     for p in lk["pieces"]]
            md.append(f"- {head} · {money(lk['total'])} new: " + " + ".join(parts) + (f" _({lk['note']})_" if lk.get("note") else ""))
        md.append("")
    md.append("_Prices and stock change fast; check the shop before you buy._")
    return "\n".join(md)


def to_text(md: str) -> str:
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", md)
    t = re.sub(r"~~(.*?)~~", r"(was \1)", t)
    t = re.sub(r"^#+\s*", "", t, flags=re.M)
    t = re.sub(r"<(https?://[^>\s]+)>", r"\1", t)
    return t.replace("  \n", "\n")


def to_html(md: str) -> str:
    out = []
    for raw in md.split("\n"):
        ln = html.escape(raw)
        ln = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", ln)
        ln = re.sub(r"~~(.*?)~~", r"<s>\1</s>", ln)
        ln = re.sub(r"&lt;(https?://[^&]+)&gt;", r'<a href="\1">\1</a>', ln)
        ln = re.sub(r"^_(.*)_$", r"<i>\1</i>", ln)
        if ln.startswith("# "):
            ln = f"<h1>{ln[2:]}</h1>"
        elif ln.startswith("## "):
            ln = f"<h2>{ln[3:]}</h2>"
        elif ln.startswith("- "):
            ln = f"<li>{ln[2:]}</li>"
        elif ln.startswith("  "):
            ln = f"<div class=u>{ln.strip()}</div>"
        out.append(ln)
    return "\n".join(out)

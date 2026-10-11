"""The no-repeat ledger. Why it exists: one early version of this showed the same hoodie 23 times in a fortnight;
148 "picks" were really 61 products. Every section shares this one ledger.

An item you've been shown stays out for `days` (default 14) unless it's worth telling you again:
  - it got cheaper again by at least `redrop` (default 5%), or
  - it came back into your size.
Colourways count as the same product, so "Hoodie - Black" and "Hoodie - Navy" don't take turns.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from . import catalog
from .store import data_dir, load_json, now_iso, save_json

_COLOUR_WORDS = sorted({w for ws in catalog.COLOUR_FAMILIES.values() for w in ws.split()}, key=len, reverse=True)
_COLOUR_TAIL = re.compile(r"[\s\-/|,]+(?:" + "|".join(map(re.escape, _COLOUR_WORDS)) + r")(?:[\s\-/]+\w+)?\s*$", re.I)


_SEGMENT = re.compile(r"\s+(?:-|–|\||/)\s+")
_HAS_COLOUR = re.compile(r"\b(?:" + "|".join(map(re.escape, _COLOUR_WORDS)) + r")\b", re.I)


def family_key(it: dict) -> str:
    title = (it.get("title") or "").strip()
    parts = _SEGMENT.split(title)
    while len(parts) > 1 and _HAS_COLOUR.search(parts[-1]):
        parts.pop()                         # "Coach jacket - pastel yellow check", "Tee | Cotton | Black"
    title = " ".join(parts)
    for _ in range(2):
        title = _COLOUR_TAIL.sub("", title)
    host = urlparse(it.get("url") or "").netloc.lower()
    return f"{host or it.get('source')}|{re.sub(r'[^a-z0-9]+', ' ', title.lower()).strip()}"


class Ledger:
    def __init__(self, path=None, days: int = 14, redrop: float = 0.95):
        self.path = path or (data_dir() / "shown.json")
        self.days, self.redrop = days, redrop
        self.rows = load_json(self.path, {})

    def verdict(self, it: dict, now: datetime | None = None) -> tuple[bool, str | None]:
        """-> (show?, label). label is None for new items, '🔁 ...' for a worthwhile re-show."""
        row = self.rows.get(family_key(it))
        if not row:
            return True, None
        now = now or datetime.now(timezone.utc)
        if now - datetime.fromisoformat(row["last"]) > timedelta(days=self.days):
            return True, None
        price, last_price = it.get("price"), row.get("price")
        if price is not None and last_price and price <= last_price * self.redrop:
            return True, f"🔁 cheaper again: {last_price:g} → {price:g}"
        back = set(it.get("my_sizes") or []) - set(row.get("sizes") or [])
        if back and not row.get("sizes"):
            return True, "🔁 back in your size"
        return False, None

    def filter(self, items: list[dict]) -> list[dict]:
        out, seen = [], set()
        for it in items:
            k = family_key(it)
            if k in seen:
                continue                    # never twice in the same digest
            ok, label = self.verdict(it)
            if ok:
                seen.add(k)
                out.append({**it, "reshow": label} if label else it)
        return out

    def note_sold_out(self, all_items: list[dict], in_size: list[dict]) -> None:
        """A product we showed that's still listed but no longer in your size: remember that, so it can come back
        as '🔁 back in your size' instead of staying hidden for the rest of the fortnight."""
        fit = {family_key(i) for i in in_size}
        listed = {family_key(i) for i in all_items}
        changed = False
        for k, row in self.rows.items():
            if k in listed and k not in fit and row.get("sizes"):
                row["sizes"] = []
                changed = True
        if changed:
            save_json(self.path, self.rows)

    def record(self, items: list[dict]) -> None:
        stamp = now_iso()
        for it in items:
            k = family_key(it)
            row = self.rows.get(k, {"first": stamp, "times": 0})
            row.update(last=stamp, price=it.get("price"), sizes=it.get("my_sizes") or [], times=row["times"] + 1,
                       title=it.get("title"))
            self.rows[k] = row
        save_json(self.path, self.rows)

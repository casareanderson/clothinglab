"""Where the digest goes. Default: stdout / a file. Optional: a Discord webhook, or email over SMTP.
Secrets come from the environment, never from config files you might commit."""
from __future__ import annotations

import json
import os
import smtplib
import urllib.request
from email.message import EmailMessage
from pathlib import Path

from .digest import to_html, to_text


def to_file(md: str, path: str) -> str:
    Path(path).expanduser().write_text(md, encoding="utf-8")
    return path


def discord_webhook(md: str, url: str | None = None) -> int:
    """Posts in <=1900-char chunks. URL from CLOTHINGLAB_DISCORD_WEBHOOK."""
    url = url or os.environ.get("CLOTHINGLAB_DISCORD_WEBHOOK")
    if not url:
        raise RuntimeError("set CLOTHINGLAB_DISCORD_WEBHOOK")
    chunks, cur = [], ""
    for ln in md.split("\n"):
        if len(cur) + len(ln) + 1 > 1900:
            chunks.append(cur)
            cur = ""
        cur += ln + "\n"
    chunks.append(cur)
    for c in chunks:
        body = json.dumps({"content": c, "flags": 4, "allowed_mentions": {"parse": []}}).encode()   # 4 = no link previews
        urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json",
                                                                              "User-Agent": "ClothingLab"}), timeout=30)
    return len(chunks)


def email(md: str, to: str, subject: str = "ClothingLab: in your size today") -> None:
    """SMTP via CLOTHINGLAB_SMTP_HOST / _PORT / _USER / _PASSWORD / _FROM (STARTTLS)."""
    e = os.environ
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, e.get("CLOTHINGLAB_SMTP_FROM", e.get("CLOTHINGLAB_SMTP_USER", "")), to
    msg.set_content(to_text(md))
    msg.add_alternative(f"<html><body style='font-family:sans-serif'>{to_html(md)}</body></html>", subtype="html")
    with smtplib.SMTP(e["CLOTHINGLAB_SMTP_HOST"], int(e.get("CLOTHINGLAB_SMTP_PORT", "587")), timeout=30) as s:
        s.starttls()
        if e.get("CLOTHINGLAB_SMTP_USER"):
            s.login(e["CLOTHINGLAB_SMTP_USER"], e["CLOTHINGLAB_SMTP_PASSWORD"])
        s.send_message(msg)

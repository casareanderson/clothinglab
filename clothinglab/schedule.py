"""Weekly digest scheduling. Installs/removes a single crontab line, marked so it's idempotent.

The cron runs `refresh` then `digest --mark-shown` and delivers via Discord, email, Telegram or
WhatsApp, so the line carries whatever the matching CLOTHINGLAB_* env points at.
"""
from __future__ import annotations

import shutil
import subprocess

MARKER = "# clothinglab-schedule"


def _current() -> str:
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def _write(lines: list[str]) -> None:
    p = subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(f"crontab update failed: {p.stderr.strip()}")


def install(command: str) -> str:
    """Install `command` as the schedule, replacing any previous clothinglab line."""
    lines = [l for l in _current().splitlines() if MARKER not in l]
    lines.append(f"{command} {MARKER}")
    _write(lines)
    return command


def remove() -> bool:
    """Remove the clothinglab schedule line. True if one was removed."""
    cur = _current().splitlines()
    lines = [l for l in cur if MARKER not in l]
    if len(lines) == len(cur):
        return False
    _write(lines)
    return True


def current() -> str | None:
    """The active clothinglab schedule line, without the marker."""
    for l in _current().splitlines():
        if MARKER in l:
            return l.replace(MARKER, "").strip()
    return None


def cron(day: int, time: str, deliver: str, email: str | None) -> str:
    """Build the cron command: `<minute> <hour> * * <day> <bin> refresh && <bin> digest --mark-shown <deliver>`."""
    try:
        hour, minute = (int(x) for x in time.split(":"))
    except ValueError:
        raise ValueError(f"bad time {time!r}, use HH:MM")
    if not 0 <= hour <= 23 or not 0 <= minute <= 59 or not 0 <= day <= 6:
        raise ValueError(f"day must be 0-6 (0=Sun) and time HH:MM — got day={day} time={time}")
    binpath = shutil.which("clothinglab") or "clothinglab"
    if deliver == "email":
        if not email:
            raise ValueError("--deliver email needs --email ADDRESS")
        send = f"--email {email}"
    else:
        send = f"--{deliver}"     # discord | telegram | whatsapp
    return f"{minute} {hour} * * {day} {binpath} refresh && {binpath} digest --mark-shown {send}"

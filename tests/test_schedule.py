import pytest

from clothinglab import schedule


def test_cron_default_weekly_discord(monkeypatch):
    monkeypatch.setattr(schedule.shutil, "which", lambda n: "/usr/local/bin/clothinglab")
    line = schedule.cron(1, "8:25", "discord", None)
    assert line == "25 8 * * 1 /usr/local/bin/clothinglab refresh && /usr/local/bin/clothinglab digest --mark-shown --discord"


def test_cron_email_requires_address():
    with pytest.raises(ValueError):
        schedule.cron(1, "8:25", "email", None)


def test_cron_email_line(monkeypatch):
    monkeypatch.setattr(schedule.shutil, "which", lambda n: "clothinglab")
    line = schedule.cron(3, "9:00", "email", "you@example.com")
    assert line == "0 9 * * 3 clothinglab refresh && clothinglab digest --mark-shown --email you@example.com"


def test_cron_rejects_bad_values():
    for day, time in ((7, "8:25"), (1, "25:00"), (1, "8:60"), (1, "not-a-time")):
        with pytest.raises(ValueError):
            schedule.cron(day, time, "discord", None)


def test_install_replaces_previous_line(monkeypatch):
    monkeypatch.setattr(schedule, "_current", lambda: "0 9 * * * other\nold line # clothinglab-schedule\n")
    written = {}
    monkeypatch.setattr(schedule, "_write", lambda lines: written.setdefault("lines", lines))
    schedule.install("25 8 * * 1 clothinglab refresh && clothinglab digest --mark-shown --discord")
    assert written["lines"][-1].endswith("# clothinglab-schedule")
    assert sum("# clothinglab-schedule" in l for l in written["lines"]) == 1


def test_remove_and_remove_nothing(monkeypatch):
    written = {}
    monkeypatch.setattr(schedule, "_write", lambda lines: written.setdefault("lines", lines))
    monkeypatch.setattr(schedule, "_current", lambda: "keep # clothinglab-schedule\nother\n")
    assert schedule.remove() is True
    assert written["lines"] == ["other"]
    written.clear()
    monkeypatch.setattr(schedule, "_current", lambda: "other\n")
    assert schedule.remove() is False

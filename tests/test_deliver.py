import json

import pytest

from clothinglab import deliver


class _Dummy:
    pass


def test_telegram_requires_env(monkeypatch):
    monkeypatch.delenv("CLOTHINGLAB_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("CLOTHINGLAB_TELEGRAM_CHAT_ID", raising=False)
    with pytest.raises(RuntimeError):
        deliver.telegram("hi")


def test_telegram_payload_and_chunking(monkeypatch):
    monkeypatch.setenv("CLOTHINGLAB_TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("CLOTHINGLAB_TELEGRAM_CHAT_ID", "123")
    monkeypatch.setattr(deliver, "to_text", lambda md: md)
    seen = []
    monkeypatch.setattr(deliver.urllib.request, "urlopen", lambda req, timeout=30: seen.append(req) or _Dummy())
    assert deliver.telegram("hello") == 1
    req = seen[0]
    assert req.full_url == "https://api.telegram.org/bottok/sendMessage"
    assert json.loads(req.data) == {"chat_id": "123", "text": "hello"}
    seen.clear()
    assert deliver.telegram("x" * 4500) == 2
    assert len(seen) == 2


def test_whatsapp_requires_env(monkeypatch):
    for k in ("CLOTHINGLAB_WA_TOKEN", "CLOTHINGLAB_WA_PHONE_ID", "CLOTHINGLAB_WA_TO"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError):
        deliver.whatsapp("hi")


def test_whatsapp_payload(monkeypatch):
    monkeypatch.setenv("CLOTHINGLAB_WA_TOKEN", "tok")
    monkeypatch.setenv("CLOTHINGLAB_WA_PHONE_ID", "999")
    monkeypatch.setenv("CLOTHINGLAB_WA_TO", "447700900000")
    monkeypatch.setattr(deliver, "to_text", lambda md: md)
    seen = []
    monkeypatch.setattr(deliver.urllib.request, "urlopen", lambda req, timeout=30: seen.append(req) or _Dummy())
    assert deliver.whatsapp("hi") == 1
    req = seen[0]
    assert req.full_url == "https://graph.facebook.com/v21.0/999/messages"
    assert json.loads(req.data) == {
        "messaging_product": "whatsapp", "to": "447700900000", "type": "text", "text": {"body": "hi"},
    }

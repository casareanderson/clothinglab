import pytest

from clothinglab import fetch
from clothinglab.fetch import Fetcher, FetchError


class _Resp:
    def __init__(self, status_code=200, body=b"{}"):
        self.status_code = status_code
        self._body = body

    def iter_content(self, chunk_size=65536):
        yield self._body


def test_fetcher_uses_requests_not_urllib(monkeypatch):
    """Shopify answers urllib with 429 and requests with 200 — the client is the difference, not the UA."""
    seen = {}

    def fake_get(url, timeout=None, headers=None):
        seen["url"] = url
        seen["headers"] = headers
        return _Resp(200, b"hello")

    monkeypatch.setattr(fetch.requests, "get", fake_get)
    f = Fetcher(user_agent="ClothingLab/test")
    assert f._raw("https://example.com/products.json") == b"hello"
    assert seen["headers"]["User-Agent"] == "ClothingLab/test"
    assert f.request_count == 1


def test_fetcher_raises_on_bad_status(monkeypatch):
    monkeypatch.setattr(fetch.requests, "get", lambda url, timeout=None, headers=None: _Resp(429, b""))
    f = Fetcher(user_agent="ClothingLab/test")
    with pytest.raises(FetchError) as e:
        f._raw("https://example.com/products.json")
    assert "429" in str(e.value)


def test_fetcher_raises_on_request_exception(monkeypatch):
    def boom(url, timeout=None, headers=None):
        raise fetch.requests.RequestException("boom")

    monkeypatch.setattr(fetch.requests, "get", boom)
    f = Fetcher(user_agent="ClothingLab/test")
    with pytest.raises(FetchError):
        f._raw("https://example.com/products.json")


def test_fetcher_refuses_placeholder_ua():
    with pytest.raises(FetchError):
        Fetcher(user_agent="ClothingLab/0.1 (CHANGE-ME: your email)")

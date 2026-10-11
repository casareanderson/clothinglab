"""A polite fetcher: robots.txt, a per-host delay, a User-Agent YOU set, timeouts, and public addresses only.

Shops are run by people. ClothingLab reads the public product data a shop already publishes (Shopify's
products.json, JSON-LD on product pages), slowly, and stops when told no.
"""
from __future__ import annotations

import ipaddress
import json
import socket
import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urlparse


PLACEHOLDER_UA = "CHANGE-ME"


class FetchError(RuntimeError):
    pass


def public_url(url: str, allow_private: bool = False) -> bool:
    """http(s) to a public address only, so a link from anywhere can't make it read your own network."""
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    if allow_private:
        return True
    try:
        infos = socket.getaddrinfo(u.hostname, None)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


class Fetcher:
    def __init__(self, user_agent: str, delay: float = 2.0, timeout: float = 20.0, allow_private: bool = False):
        if not user_agent or PLACEHOLDER_UA in user_agent:
            raise FetchError("set `user_agent` in config.yaml to something that identifies you (see config.example.yaml)")
        self.ua, self.delay, self.timeout, self.allow_private = user_agent, float(delay), float(timeout), allow_private
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._last: dict[str, float] = {}
        self.requests = 0

    def _robots_for(self, url: str):
        u = urlparse(url)
        base = f"{u.scheme}://{u.netloc}"
        if base not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                body = self._raw(base + "/robots.txt").decode("utf-8", "replace")
                rp.parse(body.splitlines())
            except FetchError:
                rp = None          # no robots.txt (or unreachable): nothing to obey
            self._robots[base] = rp
        return self._robots[base]

    def allowed(self, url: str) -> bool:
        rp = self._robots_for(url)
        return True if rp is None else rp.can_fetch(self.ua, url)

    def _wait(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            gap = self.delay - (time.monotonic() - last)
            if gap > 0:
                time.sleep(gap)
        self._last[host] = time.monotonic()

    def _raw(self, url: str) -> bytes:
        if not public_url(url, self.allow_private):
            raise FetchError(f"refusing non-public or non-http URL: {url}")
        host = urlparse(url).netloc
        self._wait(host)
        req = urllib.request.Request(url, headers={"User-Agent": self.ua, "Accept": "application/json, text/html;q=0.9"})
        self.requests += 1
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.read(15 * 1024 * 1024)
        except urllib.error.HTTPError as e:
            raise FetchError(f"HTTP {e.code} for {url}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise FetchError(f"{type(e).__name__} for {url}: {e}") from None

    def get(self, url: str) -> bytes:
        if not self.allowed(url):
            raise FetchError(f"robots.txt disallows {url}")
        return self._raw(url)

    def json(self, url: str):
        try:
            return json.loads(self.get(url).decode("utf-8", "replace"))
        except ValueError as e:
            raise FetchError(f"not JSON: {url}") from e

    def text(self, url: str) -> str:
        return self.get(url).decode("utf-8", "replace")

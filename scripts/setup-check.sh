#!/usr/bin/env bash
# Follows docs/SETUP.md step by step on a fresh machine, with tests/fake_shop.py standing in for real shops
# (CI shouldn't hit real shops every week). Fails loudly if any step in the guide stops working.
set -euo pipefail
cd "$(dirname "$0")/.."
export CLOTHINGLAB_HOME="$(mktemp -d)"
step() { printf '\n== %s\n' "$*"; }

step "1. install"
python3 -m venv .venv-check
. .venv-check/bin/activate
pip install -q -e .
clothinglab --help >/dev/null

step "2. init writes config.yaml + profile.yaml"
clothinglab init
test -f "$CLOTHINGLAB_HOME/config.yaml" && test -f "$CLOTHINGLAB_HOME/profile.yaml"

step "3. the placeholder user_agent is refused until you change it"
if clothinglab refresh 2>"$CLOTHINGLAB_HOME/err.txt"; then echo "refresh ran with the placeholder UA" >&2; exit 1; fi
grep -q user_agent "$CLOTHINGLAB_HOME/err.txt" || { cat "$CLOTHINGLAB_HOME/err.txt"; exit 1; }

step "4. point it at a shop (the fake one) and set a user agent"
python3 tests/fake_shop.py --port 8765 & SHOP=$!
trap 'kill $SHOP 2>/dev/null || true' EXIT
for _ in $(seq 20); do curl -fs http://127.0.0.1:8765/robots.txt >/dev/null && break; sleep 0.3; done
cat > "$CLOTHINGLAB_HOME/config.yaml" <<'YAML'
user_agent: "ClothingLab setup-check (github actions)"
politeness: {delay_seconds: 0, allow_private_hosts: true}
sources:
  - {name: fake-shop, adapter: shopify, url: "http://127.0.0.1:8765"}
YAML

step "5. onboarding from answers (the interview's output)"
clothinglab onboard --answers clothinglab/examples/answers.example.json --force
clothinglab validate

step "6. refresh, picks, looks, digest"
clothinglab refresh | tee "$CLOTHINGLAB_HOME/refresh.txt"
grep -q "in stock in your size" "$CLOTHINGLAB_HOME/refresh.txt"
clothinglab picks
clothinglab looks
clothinglab digest --no-watch --mark-shown --out "$CLOTHINGLAB_HOME/digest.md"
grep -q "Top picks in your size" "$CLOTHINGLAB_HOME/digest.md"

step "7. no repeats: a second digest shows none of the first one's picks"
clothinglab digest --no-watch --out "$CLOTHINGLAB_HOME/digest2.md"
python3 - "$CLOTHINGLAB_HOME" <<'PY'
import re, sys
first = set(re.findall(r"<(http[^>]+)>", open(f"{sys.argv[1]}/digest.md").read().split("## 👔")[0]))
second = set(re.findall(r"<(http[^>]+)>", open(f"{sys.argv[1]}/digest2.md").read().split("## 👔")[0]))
assert first and not first & second, (first & second)
print("no repeats:", len(first), "first-time picks, 0 shown again")
PY

step "8. watchlist"
clothinglab watch add http://127.0.0.1:8765/products/court-trainer-white --target 70
clothinglab watch check
clothinglab watch list

step "9. MCP server answers over stdio"
python3 - <<'PY'
import asyncio, json, os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    async with stdio_client(StdioServerParameters(command="clothinglab", args=["mcp"],
            env={"CLOTHINGLAB_HOME": os.environ["CLOTHINGLAB_HOME"], "PATH": os.environ["PATH"]})) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            names = [t.name for t in (await s.list_tools()).tools]
            assert "clothinglab_todays_picks" in names, names
            res = await s.call_tool("clothinglab_search", {"category": "footwear"})
            rows = json.loads(res.content[0].text)
            assert isinstance(rows, list), rows
            assert rows and all(r["category"] == "footwear" for r in rows)
            print(len(names), "tools; footwear in your size:", [r["title"] for r in rows])
asyncio.run(main())
PY

printf '\nsetup-check: every step in docs/SETUP.md worked\n'

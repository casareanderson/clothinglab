# Setting up ClothingLab

About 10 minutes. Every step below is run on a fresh Ubuntu machine by `.github/workflows/setup-check.yml`
(via `scripts/setup-check.sh`) every week, against the made-up shop in `tests/fake_shop.py`. The parts it can't
prove are marked **(not checked by CI)**.

## 1. Requirements

- Python 3.10 or newer (`python3 --version`).
- Internet access to the shops you want to read.
- Somewhere to keep two small private files. The default is `~/.clothinglab`; set `CLOTHINGLAB_HOME` to move it.

## 2. Install

```bash
pipx install git+https://github.com/casareanderson/clothinglab
# or, from a clone:
python3 -m venv .venv && . .venv/bin/activate && pip install -e .
clothinglab --help
```

## 3. Create your files

```bash
clothinglab init
```

Expected:

```
wrote /home/you/.clothinglab/config.yaml
wrote /home/you/.clothinglab/profile.yaml
next: edit config.yaml (set user_agent, pick sources), then `clothinglab onboard`
```

`init` never overwrites existing files unless you pass `--force`.

## 4. Edit config.yaml

1. **Set `user_agent`.** Something that identifies you, e.g. `"ClothingLab (personal use; you@example.com)"`.
   Until the `CHANGE-ME` placeholder is gone, `clothinglab refresh` stops with:
   `set user_agent in config.yaml to something that identifies you`.
2. **Pick your shops.** The four in the example are UK Shopify shops whose public catalogue lists stock per size.
   Keep the ones you'd buy from, add your own. For a Shopify shop you only need `name`, `adapter: shopify` and `url`.
   To read only a sale page, add `collection: <handle>` (the bit after `/collections/` in the shop's sale URL).
3. **Leave `politeness` alone** unless you have a reason. `allow_private_hosts` is for testing only.

How to tell whether a shop will work: open `https://the-shop/products.json?limit=1` in a browser. If you see JSON
with `variants` that have an `available` field, the Shopify adapter will work. **(not checked by CI: real shops)**

## 5. The onboarding interview

```bash
clothinglab onboard
```

It asks about sizes, fit, colours, brands, budget tiers and pieces you own, then writes `profile.yaml`. Required
questions are marked `*`. It never asks for height or weight.

Already have answers in a file (for example from your AI assistant)? `clothinglab onboard --answers answers.json`.
The format is in `clothinglab/examples/answers.example.json`. If `profile.yaml` exists it writes
`profile.new.yaml` instead, unless you pass `--force` (which keeps a `.bak`).

Check it:

```bash
clothinglab validate      # "profile OK"
```

## 6. First run

```bash
clothinglab refresh
clothinglab picks
clothinglab looks
clothinglab digest
```

`refresh` prints one line per shop and a total, e.g.:

```
  fake-shop                    ok 13 products
13 products checked, 12 in stock in your size
```

A shop that fails says why (`HTTP 403`, `robots.txt disallows …`) and the others carry on.

With real shops, `refresh` takes a while on purpose: there's a 2-second gap between requests to the same shop.

## 7. Make it daily

`--mark-shown` records what the digest showed, so tomorrow's doesn't repeat it:

```bash
crontab -e
25 8 * * * clothinglab refresh >/dev/null && clothinglab digest --mark-shown --out ~/clothinglab-today.md
```

Sending it somewhere **(not checked by CI)**:

- Discord: set `CLOTHINGLAB_DISCORD_WEBHOOK` and add `--discord`.
- Email: set `CLOTHINGLAB_SMTP_HOST`, `CLOTHINGLAB_SMTP_PORT` (587), `CLOTHINGLAB_SMTP_USER`,
  `CLOTHINGLAB_SMTP_PASSWORD`, `CLOTHINGLAB_SMTP_FROM`, and add `--email you@example.com`.

Remember cron has a minimal environment: put those variables in the crontab or a wrapper script.

## 8. Watchlist

```bash
clothinglab watch add https://shop.example/products/some-trainer --target 70
clothinglab watch check     # "no drops" the first time: it records the price
clothinglab watch list
```

The digest includes watchlist drops automatically (skip with `--no-watch`).

## 9. Your AI assistant

```bash
clothinglab mcp     # MCP server on stdio
```

Client config is in [MCP.md](MCP.md). Always pass `CLOTHINGLAB_HOME` in the client's `env`. MCP clients start the
server with almost no environment, so without it the server looks in the wrong place and replies
"no profile … run `clothinglab onboard` first". CI starts the server and calls two tools; the client apps
themselves are **(not checked by CI)**.

## Common problems

| You see | Why | Fix |
|---|---|---|
| `set user_agent in config.yaml…` | the placeholder is still there | edit `user_agent` |
| `no profile at …/profile.yaml` | onboarding not done, or the wrong `CLOTHINGLAB_HOME` | `clothinglab onboard`, or set the env var |
| `robots.txt disallows …` | the shop asked bots not to read that page | remove that source |
| `HTTP 403` / `HTTP 429` | the shop is blocking or rate-limiting you | remove the source or raise `delay_seconds` |
| `refusing non-public or non-http URL` | a source points at your own network | only for testing: `allow_private_hosts: true` |
| `0 in stock in your size` | the shop doesn't publish per-size stock, or nothing fits | check `products.json` has `available` per variant; check `profile.yaml` sizes |
| a shoe never matches | the shop lists US sizes as bare numbers | add `shoe_scale: us` to that source |

## Updating and removing

```bash
pipx upgrade clothinglab          # or: git pull && pip install -e .
pipx uninstall clothinglab
rm -rf ~/.clothinglab             # your profile, pool, ledger and watchlist
```

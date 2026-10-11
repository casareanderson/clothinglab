# ClothingLab

Sale clothes that are actually in stock in your size, menswear or womenswear, from shops you choose, with one look per budget tier and nothing shown twice. It's a CLI, an MCP server for your AI assistant, and a daily digest.

![A ClothingLab digest for a made-up person: top picks with the size that's in stock, budget tier and why it was picked, then one look per tier](docs/digest.png)

*A real digest, generated from the fake shop in `tests/fake_shop.py` for a made-up menswear person ("Sam", tops M/L, waist 32, UK 9/9.5). A womenswear example is [further down](#womenswear).*

![AGPL-3.0 licence](https://img.shields.io/badge/licence-AGPL--3.0-blue) ![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue) ![status: early](https://img.shields.io/badge/status-early-orange)

## Contents

- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [Usage](#usage)
- [Womenswear](#womenswear)
- [Use it from your AI assistant (MCP)](#use-it-from-your-ai-assistant-mcp)
- [Configuration](#configuration)
- [How it works](#how-it-works)
- [Status, limits and real results](#status-limits-and-real-results)
- [Licence and credits](#licence-and-credits)

## What it does

- **Only shows what's in stock in your size.** It reads each variant's size and stock flag, so a hoodie with only M left never reaches someone who wears L. Items where the shop doesn't publish per-size stock are left out, not guessed.
- **Understands real size labels**, men's and women's: `XX-Large` = `2XL` = `XXL`, `W32 L30`, `32R`, `UK 10`, `EU 38`, `S/10`, `8-10`, `10 Petite`, Shopify's glued `44 2/3 / Cream / Blue`, and bare EU shoe sizes (worked out from your UK size on the right chart). It throws out youth sizes like `6Y` or `5.5 GS`.
- **Menswear, womenswear or both**, with petite, tall and maternity ranges left out unless you shop them.
- **Budget tiers 💸 Low / 👌 Mid / 💎 High** by plain £ lines per garment (a tee under £25 is Low), which you can move.
- **Never repeats itself.** Anything you've been shown stays out for 14 days, unless it got 5% cheaper again or came back into your size. Colourways count as the same product.
- **Builds one look per tier**, a dress and shoes or a top, bottom and shoes, plus a coat if one goes, using pieces you already own when it helps. When no shoes in your size are on sale it builds top + bottom and says so, and it says when a tier has no look at all.
- **Sale items only, by default**, because a shop's whole catalogue isn't a deal. Accessories are opt-in, and shorts or flip-flops sink to the bottom between October and March (parkas in summer) and never make a look.
- **Watches products** for a price drop or a target price.
- **Asks before it assumes.** A short onboarding interview writes your profile. It never asks for height or weight.

## Quick start

You need Python 3.10 or newer.

```bash
pipx install git+https://github.com/casareanderson/clothinglab    # or: pip install -e . from a clone
clothinglab init          # writes ~/.clothinglab/config.yaml and profile.yaml
```

Open `~/.clothinglab/config.yaml`, set `user_agent` to something that identifies you (it refuses to run until you do), and add the shops you buy from. Then:

```bash
clothinglab onboard       # the interview: sizes, fit, colours, brands, budget
clothinglab refresh       # fetch the shops (slow and polite)
clothinglab digest        # today's picks and looks
```

Success looks like `N products checked, M in stock in your size` from `refresh`, and a digest like the one above. The full walk-through, with what to expect at each step, is in [docs/SETUP.md](docs/SETUP.md); a GitHub Action runs that guide on a fresh machine every week.

## Usage

![refresh, looks and search in a terminal](docs/terminal.png)

*Real output against the fake shop. The trail runner is listed in EU sizes; ClothingLab matched EU 44 and 44.5 to UK 9 and 9.5.*

| Command | What it does |
|---|---|
| `clothinglab refresh` | Fetch every source and keep the pool |
| `clothinglab picks` | Today's picks you haven't seen, one per tier first |
| `clothinglab search --category footwear --tier low --max-price 60 --query navy` | Ask the pool a question |
| `clothinglab looks` | One look per budget tier |
| `clothinglab digest --mark-shown --out today.md` | The digest; `--mark-shown` records it so tomorrow doesn't repeat |
| `clothinglab digest --discord` / `--email you@example.com` | Send it (webhook / SMTP from environment variables) |
| `clothinglab watch add URL --target 60` / `watch check` | Watch a product |

`clothinglab digest --dry-run` prints the digest without recording or sending it. A daily digest is one cron line: `25 8 * * * clothinglab refresh && clothinglab digest --mark-shown --email you@example.com`.

## Womenswear

![A ClothingLab digest for a made-up womenswear person: a dress, blouse, coat, boots, skirt and jumper in Alex's sizes, and a dress-based look](docs/digest-womens.png)

*Real output from the same fake shop for "Alex" (UK 10/12, S/M, W28 regular, UK 5/5.5). The petite jeans, the maternity dress, the bodycon dress (a cut Alex never wears) and every men's item were left out.*

- Set `department: womens` (or `both`) in the profile; the interview asks this first and then only the questions that apply.
- Sizes: UK dress sizes (EU and US labels are converted: UK 10 = EU 38 = US 6), letters, jeans by waist and leg, and UK shoe sizes on the women's chart (UK 5 = EU 38). A 30" leg counts as regular on women's jeans and short on men's.
- Shops that only sell womenswear rarely say "women's" on each product, so give the source `department: womens` in config.
- The budget lines for dresses, skirts and boots are starting points, not measured yet. Move them.

## Use it from your AI assistant (MCP)

`clothinglab mcp` runs an MCP server on stdio with 10 tools: `clothinglab_questions`, `clothinglab_save_profile`, `clothinglab_profile`, `clothinglab_refresh`, `clothinglab_search`, `clothinglab_todays_picks`, `clothinglab_digest`, `clothinglab_watch_add`, `clothinglab_watch_list`, `clothinglab_watch_check`. A new person can be onboarded entirely in chat.

Claude Desktop (`claude_desktop_config.json`), Cursor (`.cursor/mcp.json`) and most other clients use the same shape:

```json
{
  "mcpServers": {
    "clothinglab": {
      "command": "clothinglab",
      "args": ["mcp"],
      "env": { "CLOTHINGLAB_HOME": "/home/you/.clothinglab" }
    }
  }
}
```

Claude Code: `claude mcp add clothinglab -e CLOTHINGLAB_HOME=$HOME/.clothinglab -- clothinglab mcp`. Pass `CLOTHINGLAB_HOME` explicitly: MCP clients don't hand their own environment to the server. More clients, and the skill file for agents that use skills, are in [docs/MCP.md](docs/MCP.md) and [skills/clothinglab/SKILL.md](skills/clothinglab/SKILL.md).

## Configuration

Two files in `$CLOTHINGLAB_HOME` (default `~/.clothinglab`), both written owner-only.

**`config.yaml`**: where to look. See [clothinglab/examples/config.example.yaml](clothinglab/examples/config.example.yaml).

| Key | Default | What it does |
|---|---|---|
| `user_agent` | placeholder | Who you are, sent to every shop. Must be changed before anything runs |
| `politeness.delay_seconds` | `2` | Gap between requests to the same shop |
| `politeness.timeout_seconds` | `20` | Per request |
| `politeness.allow_private_hosts` | `false` | Only for testing against a shop on your own machine |
| `sources[]` | 7 example UK Shopify shops (4 men's/unisex, 3 women's) | `name`, `adapter` (`shopify`, `jsonld` or `module:function`), `url`, optional `collection`, `department`, `currency`, `shoe_scale`, `max_pages` |
| `tiers.caps` | built-in table | £ lines per garment: `{tee: {low: 25, high: 80}}` |
| `digest.picks` | `6` | Picks per digest |
| `digest.sale_only` | `true` | Only reduced items; `false` lets full-price items in |

Extra shops can go in `sources.local.yaml` next to `config.yaml` (a list in the same format); a local source with the same name replaces the one in `config.yaml`.

**`profile.yaml`**: who you are, written by `clothinglab onboard`. See [clothinglab/examples/profile.example.yaml](clothinglab/examples/profile.example.yaml).

| Key | What it does |
|---|---|
| `department` | `mens`, `womens` or `both` (default `mens`) |
| `sizes.tops` / `bottoms_letter` | Letter sizes, best fit first |
| `sizes.dress_uk` | UK dress sizes (womenswear) |
| `sizes.ranges` | Any of `petite`, `tall`, `maternity`; others are left out |
| `sizes.waist` / `trouser_length` | Waist in inches; `short`, `regular` or `long` |
| `sizes.shoes_uk` | UK shoe sizes; EU and US are worked out on the men's or women's chart |
| `fit.likes` / `fit.never` | Fit words that score up / remove an item (`skinny`) |
| `colours.palette` / `avoid` | Colours that score up / remove an item |
| `brands.love` / `never` | Brands that score up / never appear |
| `budget.tiers` / `caps` | Which tiers you want, and your own £ lines |
| `wardrobe` | Pieces you own that looks can use |
| `accessories` | `true` lets bags, hats and belts be picks (default off) |

**Environment**: `CLOTHINGLAB_HOME`, `CLOTHINGLAB_DISCORD_WEBHOOK`, `CLOTHINGLAB_SMTP_HOST`, `_PORT`, `_USER`, `_PASSWORD`, `_FROM`.

## How it works

```mermaid
flowchart LR
  S[Shops you chose] -->|products.json / JSON-LD, robots.txt, delay| G[gather]
  G --> P[(pool)]
  P --> Z[in your size?]
  Z --> R[rank + tier]
  R --> L{seen in 14 days?}
  L -->|new, cheaper again, back in size| D[digest / MCP / CLI]
  R --> K[looks per tier]
  K --> D
  D --> X[(shown ledger)]
```

```
clothinglab/
  sources/shopify.py   any Shopify shop: per-variant size + stock from /products.json
  sources/jsonld.py    any shop with a sitemap + schema.org Product offers
  fetch.py             robots.txt, per-shop delay, your user agent, public addresses only
  sizes.py             letters, waists, UK/EU/US shoes, youth sizes
  engine.py            gather -> in your size -> rank + tier
  ledger.py            the no-repeat ledger
  looks.py             one look per tier
  watch.py             watchlist
  onboard.py           the interview -> profile.yaml
  mcp_server.py        the MCP tools
tests/fake_shop.py     a made-up shop used by the tests, the setup check and the images above
```

Adding a shop that isn't Shopify and has no usable JSON-LD: write `fetch(fetcher, src) -> list[dict]` returning items in the shape described in `clothinglab/sources/__init__.py`, and set `adapter: yourmodule:fetch`.

## Status, limits and real results

Early, version 0.1.0. Measured on 11 Oct 2026 against the fake shop (25 adult products, 13 men's and 12 women's): 12 in stock in Sam's sizes and 11 in Alex's, 10 and 9 after their own exclusions (Alex's tote bag drops out because accessories are off by default), 6 picks each, and a second digest for Sam that repeated none of the first. The unit tests (110) and the setup check, which runs both people, run on GitHub Actions.

Limits you should know about:

- **Per-size stock is the whole game, and many big high-street shops don't publish it** in their page data; they load it later with JavaScript. ClothingLab leaves those items out rather than guessing, so the starter list is Shopify shops.
- **Shoe and dress conversions use one common UK chart each** for men's and women's. Brands differ by half a size; the EU window allows half a size below. Vanity sizing isn't fixed by any chart.
- **Adults only for now.** Kids' items are dropped; the size code is structured so a kids' chart can be added.
- **A person who shops "both"** uses one shoe chart (`sizes.chart`) for items that don't say which department they're from.
- **No buying, no checkout, no accounts.** It reads public catalogue data and nothing else.
- **Be a good guest.** Respect each shop's terms. The fetcher obeys robots.txt and waits between requests, but you choose the shops.
- **Bring your own order importer.** There's no email or order-history import in this repo; see [docs/IMPORTERS.md](docs/IMPORTERS.md) for the interface.

## Licence and credits

[AGPL-3.0-or-later](LICENSE). Use it, change it, run it for yourself; if you run a modified version as a service for other people, share your changes.

The brands in `tests/fake_shop.py` (Northfold, Harbour & Pine, Ashgrove) are made up. The four example shops in `config.example.yaml` are examples of public Shopify catalogues, not endorsements.

If ClothingLab is useful to you, [buy me a coffee](https://buymeacoffee.com/iamc_tech). More field notes at [dev.to/iam-tech](https://dev.to/iam-tech).

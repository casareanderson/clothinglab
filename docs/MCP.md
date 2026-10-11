# ClothingLab in your AI assistant

`clothinglab mcp` (or `clothinglab-mcp`) is a stdio MCP server. Every client below starts it as a local command.
**Always set `CLOTHINGLAB_HOME`** in the client's environment block: clients start servers with almost no
environment of their own.

## Tools

| Tool | What it's for |
|---|---|
| `clothinglab_questions` | The onboarding interview, as sections and questions |
| `clothinglab_save_profile` | `{answers: {question_id: answer}}` -> profile.yaml (won't overwrite without `overwrite: true`) |
| `clothinglab_profile` | Show the saved profile |
| `clothinglab_refresh` | Fetch every configured shop. Slow; once a day |
| `clothinglab_search` | `category`, `tier`, `max_price`, `query`, `limit` |
| `clothinglab_todays_picks` | Picks (one per tier first) + looks, skipping what's been shown; `mark_shown` to record |
| `clothinglab_digest` | The digest as Markdown |
| `clothinglab_watch_add` / `_list` / `_check` | The watchlist |

Nothing posts, buys or signs up to anything.

## Claude Desktop

`claude_desktop_config.json`:

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

If `clothinglab` isn't on the PATH the app sees, use the full path (`which clothinglab`).

## Claude Code

```bash
claude mcp add clothinglab -e CLOTHINGLAB_HOME=$HOME/.clothinglab -- clothinglab mcp
```

## Cursor

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global): the same JSON as Claude Desktop.

## Hermes Agent and other config-file clients

Any client that takes a command, args and env works the same way. For Hermes (`config.yaml`):

```yaml
mcp_servers:
  clothinglab:
    command: clothinglab
    args: [mcp]
    env:
      CLOTHINGLAB_HOME: /home/you/.clothinglab
```

## ChatGPT, Grok and other remote-only clients

These connect to MCP servers over HTTP, not stdio. Run ClothingLab behind a stdio-to-HTTP bridge you trust
(for example `npx supergateway --stdio "clothinglab mcp" --port 8000`), put it behind authentication, and give the
client that URL. Be careful: whoever can reach that URL can read your profile and watchlist. **(not checked by CI)**

## Skills

Agents that load skills (Claude, Hermes and others) can use [../skills/clothinglab/SKILL.md](../skills/clothinglab/SKILL.md):
how to run the interview, when to refresh, and how to talk about results honestly.

#!/usr/bin/env bash
# clothinglab weekly digest — injects the Discord webhook from Infisical, then refreshes + delivers.
set -uo pipefail
export HOME=/root
export PATH=/usr/local/bin:/usr/bin:/bin
export CLOTHINGLAB_HOME=/root/.clothinglab
export CLOTHINGLAB_DISCORD_WEBHOOK="$(
  python3 -c 'import sys; sys.path.insert(0, "/opt/hermes-agent"); import hermes_secrets as hs; print(hs.get("CLOTHINGLAB_DISCORD_WEBHOOK", "/"))'
)"
clothinglab refresh
clothinglab digest --mark-shown --discord

#!/usr/bin/env bash
# Launcher for the vendored (patched) codeguilds CLI bundled with this skill.
# Resolves the CLI relative to this script so the skill works regardless of cwd
# and regardless of where ~/.claude lives. See ../vendor for why a local copy exists.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI="$DIR/../vendor/node_modules/codeguilds/dist/index.js"
if [[ ! -f "$CLI" ]]; then
  echo "codeguilds CLI not found at $CLI" >&2
  echo "Re-install it: npm install codeguilds@0.2.5 --prefix \"$DIR/../vendor\"  (then re-apply the ../package.json patch)" >&2
  exit 1
fi
exec node "$CLI" "$@"

#!/usr/bin/env bash
#
# Install one or more skills from the hub into ~/.claude/skills/
#
#   curl -fsSL https://hiyabh.github.io/claude-skills/install.sh | bash -s -- debug test-loop
#
# Never overwrites an existing skill of the same name - it is skipped instead.
set -euo pipefail

BASE_URL="https://hiyabh.github.io/claude-skills/dl"
SKILLS_DIR="${HOME}/.claude/skills"

if [ "$#" -eq 0 ]; then
  echo "Usage: bash -s -- <skill-name> [more-skill-names...]" >&2
  echo "The list of skills: https://hiyabh.github.io/claude-skills/" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$SKILLS_DIR"

fetch() {
  if command -v curl >/dev/null 2>&1; then curl -fsSL "$1" -o "$2"
  elif command -v wget >/dev/null 2>&1; then wget -q "$1" -O "$2"
  else echo "ERROR: neither curl nor wget is available." >&2; exit 1
  fi
}

installed=0; skipped=0
for name in "$@"; do
  case "$name" in *[!a-z0-9-]*|"") echo "    bad name: $name (skipped)"; continue;; esac
  if [ -e "$SKILLS_DIR/$name" ]; then
    echo "    skip  $name (already exists - not overwritten)"
    skipped=$((skipped + 1)); continue
  fi
  if ! fetch "$BASE_URL/$name.tar.gz" "$TMP/$name.tar.gz"; then
    echo "    fail  $name (not found on the hub)"; continue
  fi
  mkdir -p "$TMP/x"
  tar -xzf "$TMP/$name.tar.gz" -C "$TMP/x"
  cp -r "$TMP/x/skills/$name" "$SKILLS_DIR/$name"
  echo "    ok    $name"
  installed=$((installed + 1))
done

echo
echo "==> installed: $installed   skipped: $skipped"
echo "    location: $SKILLS_DIR"
echo "Restart Claude Code so it picks up the new skills."

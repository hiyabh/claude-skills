#!/usr/bin/env bash
#
# Install skills from the hub into ~/.claude/skills/
#
#   One or more skills:  curl -fsSL https://hiyabh.github.io/claude-skills/install.sh | bash -s -- debug test-loop
#   Everything:          curl -fsSL https://hiyabh.github.io/claude-skills/install.sh | bash -s -- all
#
# Never overwrites an existing skill of the same name - it is skipped instead.
set -euo pipefail

HUB="${SKILLS_HUB:-https://hiyabh.github.io/claude-skills}"   # override only for local testing
SKILLS_DIR="${HOME}/.claude/skills"

if [ "$#" -eq 0 ]; then
  echo "Usage: bash -s -- <skill-name> [more...]   or   bash -s -- all" >&2
  echo "The list of skills: $HUB/" >&2
  exit 1
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$SKILLS_DIR"
installed=0; skipped=0; failed=0

fetch() {
  if command -v curl >/dev/null 2>&1; then curl -fsSL "$1" -o "$2"
  elif command -v wget >/dev/null 2>&1; then wget -q "$1" -O "$2"
  else echo "ERROR: neither curl nor wget is available." >&2; exit 1
  fi
}

# Copy one skill folder into place unless a skill of that name already exists.
place() {
  local src="$1" name="$2"
  if [ -e "$SKILLS_DIR/$name" ]; then
    echo "    skip  $name (already exists - not overwritten)"; skipped=$((skipped + 1))
  else
    cp -r "$src" "$SKILLS_DIR/$name"; echo "    ok    $name"; installed=$((installed + 1))
  fi
}

# Unpack a tarball into a fresh folder and print that folder's path.
unpack() {
  local url="$1" dir
  dir="$(mktemp -d "$TMP/x.XXXX")"
  fetch "$url" "$dir/pkg.tar.gz" || return 1
  tar -xzf "$dir/pkg.tar.gz" -C "$dir" && rm -f "$dir/pkg.tar.gz"
  echo "$dir"
}

# A tarball whose root is skills/<name>/... (hub skills and the bundles).
install_bundle() {
  local dir d
  if ! dir="$(unpack "$1")"; then echo "    fail  $1"; failed=$((failed + 1)); return; fi
  for d in "$dir"/skills/*/; do place "$d" "$(basename "$d")"; done
}

# A GitHub repo tarball whose root folder *is* the skill.
install_repo() {
  local name="$1" dir
  if ! dir="$(unpack "$2")"; then echo "    fail  $name"; failed=$((failed + 1)); return; fi
  place "$(find "$dir" -mindepth 1 -maxdepth 1 -type d | head -n1)" "$name"
}

install_skill() {
  case "$1" in *[!a-z0-9-]*|"") echo "    bad name: $1 (skipped)"; return;; esac
  install_bundle "$HUB/dl/$1.tar.gz"
}

install_all() {
  echo "==> installing every skill from $HUB"
  fetch "$HUB/dl/all.txt" "$TMP/all.txt"
  while read -r kind a b; do
    case "$kind" in
      skill)  install_skill "$a" ;;
      bundle) install_bundle "$a" ;;
      repo)   install_repo "$a" "$b" ;;
    esac
  done < "$TMP/all.txt"
}

if [ "$1" = "all" ]; then install_all; else for name in "$@"; do install_skill "$name"; done; fi

echo
echo "==> installed: $installed   skipped: $skipped   failed: $failed"
echo "    location: $SKILLS_DIR"
echo "Restart Claude Code so it picks up the new skills."

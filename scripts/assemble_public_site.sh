#!/usr/bin/env bash
# Copy the public landing and token metadata into DEST.
#
# GitHub Pages and the local metadata server publish only this tree.
# Agent config, scripts, git metadata, and other repo files stay out.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-}"

if [[ -z "$DEST" || "$DEST" == "/" || "$DEST" == "$REPO_ROOT" ]]; then
  echo "usage: assemble_public_site.sh DEST" >&2
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$DEST"

copy_file() {
  local rel="$1"
  local src="$REPO_ROOT/$rel"
  if [[ ! -f "$src" ]]; then
    echo "missing public file: $rel" >&2
    exit 1
  fi
  mkdir -p "$DEST/$(dirname -- "$rel")"
  cp "$src" "$DEST/$rel"
}

copy_tree() {
  local rel="$1"
  local src="$REPO_ROOT/$rel"
  local file relpath base
  if [[ ! -d "$src" ]]; then
    echo "missing public directory: $rel" >&2
    exit 1
  fi
  while IFS= read -r -d '' file; do
    base="$(basename -- "$file")"
    case "$base" in
      .*|_*) continue ;;
    esac
    relpath="${file#"$REPO_ROOT"/}"
    mkdir -p "$DEST/$(dirname -- "$relpath")"
    cp "$file" "$DEST/$relpath"
  done < <(find "$src" -type f -print0)
}

copy_file index.html
copy_file .nojekyll
copy_file docs/index.html
copy_file docs/SOFT7-PAGES-PING.txt
copy_file gallery/index.html
copy_tree images
copy_tree meta
copy_file mask-depth-reynard/1.jpg
copy_file mask-depth-reynard/1.json
copy_file reynard-prime/meta/0.json
copy_file soft7-bg-key-01.png
copy_file soft7-bg-loop.mp4
copy_file soft7-bg-loop.webm
copy_file soft7-mascot-hero.jpg
copy_file soft7-mascot-hero.png

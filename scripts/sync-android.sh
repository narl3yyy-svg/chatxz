#!/usr/bin/env bash
# Sync main chatxz Python sources into the Android Chaquopy bundle.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/chatxz"
DST="$ROOT/android/app/src/main/python/chatxz"

echo "Syncing $SRC -> $DST"
rm -rf "$DST"
mkdir -p "$DST"

copy_tree() {
  local from="$1" to="$2"
  mkdir -p "$to"
  for entry in "$from"/*; do
    base="$(basename "$entry")"
    case "$base" in
      __pycache__) continue ;;
    esac
    if [ -d "$entry" ]; then
      copy_tree "$entry" "$to/$base"
    elif [[ "$entry" == *.pyc ]]; then
      continue
    else
      cp "$entry" "$to/$base"
    fi
  done
}

copy_tree "$SRC" "$DST"
count="$(find "$DST" -name '*.py' | wc -l | tr -d ' ')"
echo "Android Python bundle synced ($count Python files)."
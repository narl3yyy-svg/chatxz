#!/usr/bin/env python3
"""Build emoji-keywords.json from iamcal/emoji-data for picker search."""

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "chatxz" / "web" / "static" / "index.html"
OUT = ROOT / "chatxz" / "web" / "static" / "emoji-keywords.json"
URL = "https://raw.githubusercontent.com/iamcal/emoji-data/master/emoji.json"


def main():
    with urllib.request.urlopen(URL, timeout=30) as resp:
        data = json.load(resp)

    html = HTML.read_text(encoding="utf-8")
    match = re.search(r"const EMOJIS = (\[.*?\]);", html, re.S)
    if not match:
        raise SystemExit("EMOJIS array not found in index.html")
    emojis = re.findall(r"'([^']*)'", match.group(1))

    def unified_to_char(unified):
        if not unified:
            return ""
        try:
            return "".join(chr(int(part, 16)) for part in str(unified).split("-"))
        except ValueError:
            return ""

    by_char = {}
    for item in data:
        ch = unified_to_char(item.get("unified"))
        if not ch:
            continue
        parts = []
        for key in ("name", "short_name", "text"):
            val = (item.get(key) or "").lower().replace("_", " ").replace("-", " ")
            if val:
                parts.append(val)
        for sn in item.get("short_names") or []:
            parts.append(str(sn).lower().replace("_", " ").replace("-", " "))
        terms = " ".join(dict.fromkeys(" ".join(parts).split()))
        if terms:
            by_char[ch] = terms

    out = {}
    missing = []
    for e in emojis:
        terms = by_char.get(e, "")
        if not terms and e.endswith("\uFE0F"):
            terms = by_char.get(e[:-1], "")
        if not terms and not e.endswith("\uFE0F"):
            terms = by_char.get(e + "\uFE0F", "")
        if terms:
            out[e] = terms
        else:
            missing.append(e)

    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUT} — mapped {len(out)}/{len(emojis)}, missing {len(missing)}")
    if missing[:5]:
        print("missing sample:", missing[:5])


if __name__ == "__main__":
    main()
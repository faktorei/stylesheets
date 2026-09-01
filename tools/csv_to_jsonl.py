#!/usr/bin/env python3
"""faktorei · tools/csv_to_jsonl.py — CSV → batch manifest (JSONL) converter.

The batch manifest is JSONL (one JSON object per line) — one wire format, one
parser. Archive-migration customers who keep their file list in a spreadsheet can
export CSV and convert here; the manifest itself stays JSONL.

CSV header names the columns; `input` is required, `lang`/`profile`/`output` are
optional (see docs/batch-manifest.md). Empty cells are omitted (so the row→job→
engine cascade applies). Unknown columns pass through as-is — the engine ignores
unknown manifest fields with a warning, so this converter needn't know the schema.

    python3 tools/csv_to_jsonl.py files.csv > manifest.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import sys

# This tool writes an XML document that DECLARES UTF-8 to stdout, whose encoding
# is platform-dependent: on a Windows console (cp1252) the German street name
# lost its "ss" and the emitted fixture silently stopped matching the committed
# one, while still claiming UTF-8 in its prolog. Silent corruption is worse than
# a crash, so pin the stream.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass  # already UTF-8, or not a reconfigurable stream



def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", help="input CSV (a header row naming the columns)")
    ap.add_argument("-o", "--out", help="output .jsonl (default: stdout)")
    args = ap.parse_args()

    out = open(args.out, "w", encoding="utf-8", newline="\n") if args.out else sys.stdout
    n = 0
    with open(args.csv, newline="", encoding="utf-8-sig") as f:  # -sig tolerates an Excel BOM
        reader = csv.DictReader(f)
        if "input" not in (reader.fieldnames or []):
            sys.exit("error: CSV must have an 'input' column")
        for row in reader:
            obj = {k: v for k, v in row.items() if k and v not in (None, "")}
            if not obj.get("input"):
                continue  # skip rows with no input (blank trailing lines)
            out.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    if args.out:
        out.close()
    print(f"[csv_to_jsonl] wrote {n} manifest rows", file=sys.stderr)


if __name__ == "__main__":
    main()

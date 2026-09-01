#!/usr/bin/env python3
"""faktorei · tools/test_money.py — the number-formatting contract.

Separator convention is a LANGUAGE property; the number of decimal places is a
CURRENCY property. They used to be conflated: both picture strings in
render/layout.xsl hard-coded two decimals, so a JPY invoice printed 18000 as
"18,000.00" and a three-decimal currency was silently truncated. Nothing caught
it because every fixture in the corpus was in EUR.

This runs at the FO stage on purpose. FO is deterministic text produced by Saxon
alone, so these assertions need neither FOP nor poppler — they run identically on
a Windows dev box and in CI, and they do not depend on a blessed baseline.

    python3 tools/test_money.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (fixture, lang, must appear, must NOT appear, why)
CASES = [
    ("corpus/fixtures/ubl/018-jpy-zero-decimal.xml", "en",
     [">18,000<", ">22,000<", ">1,500<"],
     [">18,000.00<", ">22,000.00<", ">1,500.00<"],
     "JPY has no minor unit (ISO 4217) — whole yen, never two decimals"),

    # Quantities are not money. Routing them through the money formatter would
    # take the currency's minor units and round 2.5 to "3" on a JPY invoice.
    ("corpus/fixtures/ubl/018-jpy-zero-decimal.xml", "en",
     [">2.50<", ">12<"],
     [">3<"],
     "a fractional quantity keeps two places even on a zero-decimal currency"),

    ("corpus/fixtures/ubl/019-aud-gst.xml", "en",
     [">1,996.00<", ">2,195.60<", ">249.50<"],
     [">1,996<", ">2,195.6<"],
     "AUD has two minor units — unchanged from the pre-fix behaviour"),

    # The control: the currency lookup must not disturb the euro corpus.
    ("corpus/fixtures/ubl/001-base-multivat.xml", "en",
     [".00<"],
     [],
     "EUR still renders two decimals"),
    ("corpus/fixtures/ubl/001-base-multivat.xml", "de",
     [",00<"],
     [],
     "German convention: comma decimal, period grouping"),
]


def fo(fixture: str, lang: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "doc.fo"
        subprocess.run(
            [sys.executable, str(REPO / "tools/render.py"), str(REPO / fixture),
             str(out), "--stop-at", "fo", "--lang", lang],
            check=True, capture_output=True)
        return out.read_text(encoding="utf-8")


def main() -> int:
    failures = []
    for fixture, lang, present, absent, why in CASES:
        text = fo(fixture, lang)
        name = f"{Path(fixture).name} [{lang}]"
        for token in present:
            if token not in text:
                failures.append(f"{name}: expected {token!r} — {why}")
        for token in absent:
            if token in text:
                failures.append(f"{name}: found {token!r}, which must not appear — {why}")
        if not failures:
            print(f"[money] {name}: ok — {why}")

    # The currencies whose minor unit is not 2 must be declared in the stylesheet;
    # a silent regression to a hard-coded picture string would drop them.
    layout = (REPO / "stylesheets/render/layout.xsl").read_text(encoding="utf-8")
    for code in ("JPY", "KRW", "ISK", "CLP", "VND"):
        if code not in layout:
            failures.append(f"layout.xsl: zero-decimal currency {code} is not declared")
    for code in ("BHD", "KWD", "OMR", "TND"):
        if code not in layout:
            failures.append(f"layout.xsl: three-decimal currency {code} is not declared")
    # French groups with a no-break space, not the German period.
    if 'name="fr"' not in layout or "&#160;" not in layout:
        failures.append("layout.xsl: the French decimal-format (no-break space grouping) is missing")

    if failures:
        print(f"\n[money] FAIL — {len(failures)} problem(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"\n[money] PASS — {len(CASES)} cases, formatting is currency-aware")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""faktorei · tools/test_profile.py — the profile-delta contract.

A presentation profile is a configuration delta, never a fork. Two properties
have to hold together, and a pixel baseline can assert neither of them clearly:

  1. the delta APPLIES on its own profile (PINT A-NZ calls the tax GST), and
  2. the delta is SCOPED — it must not leak into any other profile. An
     English-language European invoice still says VAT.

(2) is the one worth a test. Wording like VAT/GST is a jurisdiction property,
not a language one, so the obvious implementation — a separate label bundle per
region — silently corrupts the other profiles that share a language.

Runs at the FO stage: deterministic text from Saxon alone, so no FOP, no
poppler, no blessed baseline.

    python3 tools/test_profile.py
"""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (fixture, lang, expected words, forbidden words, why)
CASES = [
    ("corpus/fixtures/ubl/020-pint-aunz-gst.xml", "en",
     ["GST", "GST ID", "GST breakdown", "Total GST", "Account"],
     ["VAT", "VAT breakdown", "Total VAT", "IBAN"],
     "PINT A-NZ is auto-detected from BT-24 and labels the tax GST"),

    # The control. Same language, same currency, different profile.
    ("corpus/fixtures/ubl/019-aud-gst.xml", "en",
     ["VAT", "VAT breakdown", "Total VAT"],
     ["GST breakdown", "Total GST"],
     "a Peppol BIS invoice keeps VAT wording — the override must not leak"),

    ("corpus/fixtures/ubl/001-base-multivat.xml", "en",
     ["VAT breakdown"],
     ["GST breakdown"],
     "the European corpus is untouched by the A-NZ override"),
]


def labels(fixture: str, lang: str) -> str:
    """Every text run in the FO, so a word is matched as rendered."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "doc.fo"
        subprocess.run(
            [sys.executable, str(REPO / "tools/render.py"), str(REPO / fixture),
             str(out), "--stop-at", "fo", "--lang", lang],
            check=True, capture_output=True)
        return out.read_text(encoding="utf-8")


def main() -> int:
    failures = []
    for fixture, lang, expected, forbidden, why in CASES:
        text = labels(fixture, lang)
        name = Path(fixture).name
        for word in expected:
            if f">{word}<" not in text and f">{word} <" not in text:
                failures.append(f"{name}: expected the label {word!r} — {why}")
        for word in forbidden:
            if f">{word}<" in text:
                failures.append(f"{name}: label {word!r} leaked in — {why}")
        print(f"[profile] {name}: checked — {why}")

    if failures:
        print(f"\n[profile] FAIL — {len(failures)} problem(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"\n[profile] PASS — {len(CASES)} cases, profile deltas apply and stay scoped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

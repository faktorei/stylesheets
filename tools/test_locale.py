#!/usr/bin/env python3
"""faktorei · tools/test_locale.py — every shipped locale actually renders.

Why this exists: the French number format was added with a picture string using
U+0020 while its decimal-format declared U+00A0 as the grouping separator. Saxon
rejects that ("Passive character must not appear between active characters in a
sub-picture") and EVERY French render died. Nothing caught it, because no fixture
was ever rendered in French — the corpus renders in `en`, and the pixel gate
blesses `en` baselines. A locale can therefore be completely broken while the
whole suite stays green.

So this walks every labels-*.xml the repo ships and renders a fixture in that
language, asserting:

  1. the render SUCCEEDS — which is the assertion that would have caught the
     format bug, and costs nothing;
  2. the label file is COMPLETE against labels-en.xml — a missing key silently
     renders as empty text, not as an error;
  3. its own words REACH the output — proof the file is actually consulted and
     not, say, falling back to English;
  4. no English label LEAKS into a non-English render, which is what a partially
     translated file looks like.

Asserts at the FO stage: Saxon only, no FOP and no poppler, so it runs anywhere
the reference pipeline does.

Usage: python3 tools/test_locale.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "corpus/fixtures/ubl/001-base-multivat.xml"

# A word that must appear in each language's output, and that appears in NO other
# shipped language — so finding it proves the right file was loaded.
SIGNATURE = {
    "en": "Amount due",
    "de": "Zahlbetrag",
    "fr": "Net à payer",
    "nl": "Te betalen",
}

# English labels distinctive enough that seeing them in a translated render means
# a key is missing. Deliberately not every label: "IBAN" and "Pos" are the same
# in all four languages and would false-positive.
ENGLISH_LEAKS = ["Amount due", "Total net", "Total VAT", "Unit price",
                 "Brought forward", "VAT breakdown", "Issue date", "Due date"]


def labels(lang: str) -> dict[str, str]:
    path = REPO / f"stylesheets/i18n/labels-{lang}.xml"
    return {el.get("key"): (el.text or "")
            for el in ET.parse(path).getroot().findall(".//label")}


def render_fo(lang: str, out: Path) -> tuple[bool, str]:
    r = subprocess.run(
        [sys.executable, str(REPO / "tools/render.py"), str(FIXTURE), str(out),
         "--lang", lang, "--stop-at", "fo"],
        capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout)[-300:]


def main() -> int:
    shipped = sorted(p.stem.split("-", 1)[1]
                     for p in (REPO / "stylesheets/i18n").glob("labels-*.xml"))
    if "en" not in shipped:
        print("[locale] FAIL — labels-en.xml missing; it is the reference set")
        return 1

    en = labels("en")
    failures: list[str] = []
    print(f"[locale] shipped locales: {', '.join(shipped)}")

    with tempfile.TemporaryDirectory() as td:
        for lang in shipped:
            # 2. completeness against the reference set
            these = labels(lang)
            missing = sorted(set(en) - set(these))
            empty = sorted(k for k, v in these.items() if not v.strip())
            if missing:
                failures.append(f"labels-{lang}.xml is missing {len(missing)} key(s): "
                                f"{', '.join(missing[:6])}")
            if empty:
                failures.append(f"labels-{lang}.xml has empty value(s): {', '.join(empty[:6])}")

            # 1. it renders at all
            fo = Path(td) / f"{lang}.fo"
            ok, err = render_fo(lang, fo)
            if not ok:
                failures.append(f"rendering in '{lang}' failed: {err.strip()}")
                print(f"[locale] {lang}: RENDER FAILED")
                continue
            text = fo.read_text(encoding="utf-8")

            # 3. this locale's own words reached the output
            sig = SIGNATURE.get(lang)
            if sig and sig not in text:
                failures.append(f"'{lang}' rendered without its signature label {sig!r} — "
                                f"the file may not be loaded")

            # 4. no English leaked into a translated render
            if lang != "en":
                leaked = [w for w in ENGLISH_LEAKS if w in text]
                if leaked:
                    failures.append(f"English leaked into the '{lang}' render: "
                                    f"{', '.join(leaked)}")

            print(f"[locale] {lang}: {len(these)} labels, renders, "
                  f"signature {sig!r} present" if sig else f"[locale] {lang}: ok")

    if failures:
        print(f"\n[locale] FAIL — {len(failures)} problem(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"\n[locale] PASS — {len(shipped)} locales complete and rendering")
    return 0


if __name__ == "__main__":
    sys.exit(main())

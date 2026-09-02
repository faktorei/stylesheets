#!/usr/bin/env python3
"""faktorei · tools/test_gen_fixture.py — the generator's round-trip contract.

gen_fixture.py states that its output is corpus-stable: "same N -> same bytes",
and that the committed generated fixtures must round-trip through it. That claim
is load-bearing — it is why 003 and 017 can be regenerated rather than trusted —
and nothing tested it.

It broke, quietly. The generator prints an XML document that DECLARES UTF-8 to
stdout, whose encoding is platform-dependent: on a Windows console (cp1252) the
seller's street name lost its "ss" and the emitted fixture stopped matching the
committed one while still claiming UTF-8 in its prolog. A crash would have been
kinder than silent corruption.

Line endings are normalised before comparing: git stores these fixtures with LF,
but a Windows checkout with core.autocrlf=true materialises them as CRLF, and
that difference is about the checkout, not the generator.

    python3 tools/test_gen_fixture.py
"""
import subprocess
import sys
from pathlib import Path

# Windows consoles default to cp1252, and these tools print EN 16931 rule text,
# party names and paths that carry non-ASCII — a curly quote, "Speicherstraße",
# an em dash. Printing one raised UnicodeEncodeError and killed the run mid-report:
# a finding became a traceback, which is the wrong failure mode for a tool whose
# job is to report. errors="replace" is correct HERE and would be wrong in
# gen_fixture.py / csv_to_jsonl.py, whose stdout IS the artifact — there a mangled
# character must crash rather than silently substitute.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # already UTF-8, or not a reconfigurable stream

REPO = Path(__file__).resolve().parent.parent

# (N, the committed fixture that N must reproduce)
CASES = [
    (120, "corpus/fixtures/ubl/003-lines-120.xml"),
    (500, "corpus/fixtures/ubl/017-lines-500.xml"),
]

# Non-ASCII that must survive the emit path. This is the exact character the
# cp1252 console destroyed.
MUST_SURVIVE = ["Speicherstraße", "Nordkontor Supplies GmbH"]


def generated(n: int) -> bytes:
    r = subprocess.run([sys.executable, str(REPO / "tools/gen_fixture.py"), str(n)],
                       capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"gen_fixture.py {n} failed:\n{r.stderr.decode(errors='replace')}")
    return r.stdout


def main() -> int:
    failures = []
    for n, rel in CASES:
        out = generated(n)

        # 1. It must still be UTF-8, and the non-ASCII must be intact. Checked
        #    before the comparison so a mangled emit reports as an encoding
        #    problem rather than an opaque byte mismatch.
        try:
            text = out.decode("utf-8")
        except UnicodeDecodeError as e:
            failures.append(f"gen_fixture.py {n}: output is not valid UTF-8 ({e})")
            continue
        for token in MUST_SURVIVE:
            if token not in text:
                failures.append(
                    f"gen_fixture.py {n}: {token!r} missing — the emit path mangled "
                    f"non-ASCII (a cp1252 stdout turns 'ß' into '?')")

        # 2. It must reproduce the committed fixture. Compare against the git
        #    blob, not the working tree, so a CRLF checkout cannot skew it.
        blob = subprocess.run(["git", "show", f"HEAD:{rel}"],
                              capture_output=True, cwd=REPO).stdout
        if not blob:
            failures.append(f"{rel}: not found in git — cannot check the round-trip")
            continue
        if out.replace(b"\r\n", b"\n") != blob.replace(b"\r\n", b"\n"):
            failures.append(
                f"gen_fixture.py {n} no longer reproduces {rel} "
                f"(generated {len(out)}B vs committed {len(blob)}B)")
        else:
            print(f"[gen] {n:3d} lines -> {Path(rel).name}: round-trip OK, non-ASCII intact")

    if failures:
        print(f"\n[gen] FAIL — {len(failures)} problem(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print(f"\n[gen] PASS — {len(CASES)} generated fixtures reproduce byte-for-byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())

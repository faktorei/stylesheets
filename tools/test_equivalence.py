#!/usr/bin/env python3
"""faktorei · tools/test_equivalence.py — the pivot-architecture contract.

Twin fixtures (same business content, different syntax) MUST normalize to
identical semantic XML apart from <si:meta> attributes. This is what
guarantees one rendering implementation serves every input syntax.

Twins are declared below; add a pair whenever a CII twin lands.
"""
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TWINS = [
    ("corpus/fixtures/ubl/001-base-multivat.xml",
     "corpus/fixtures/cii/101-base-multivat.xml"),
    ("corpus/fixtures/ubl/007-xrechnung-leitweg.xml",
     "corpus/fixtures/cii/107-xrechnung-leitweg.xml"),
    ("corpus/fixtures/ubl/008-exempt-e.xml",
     "corpus/fixtures/cii/108-exempt-e.xml"),
    ("corpus/fixtures/ubl/013-rounding.xml",
     "corpus/fixtures/cii/113-rounding.xml"),
]
SI = "urn:faktorei:semantic:invoice:1"


def semantic(path: Path, out: Path) -> ET.Element:
    subprocess.run([sys.executable, str(REPO / "tools/render.py"),
                    str(path), str(out), "--stop-at", "semantic"],
                   check=True, capture_output=True)
    root = ET.parse(out).getroot()
    # meta is syntax-specific by definition — normalize it out
    meta = root.find(f"{{{SI}}}meta")
    if meta is not None:
        meta.attrib.clear()
    return root


def canon(el: ET.Element, indent: int = 0) -> str:
    tag = el.tag.split("}")[-1]
    attrs = " ".join(f'{k}="{v}"' for k, v in sorted(el.attrib.items()))
    text = (el.text or "").strip()
    lines = [f"{'  ' * indent}<{tag}{' ' + attrs if attrs else ''}>{text}"]
    for child in el:
        lines.append(canon(child, indent + 1))
    return "\n".join(lines)


def main() -> None:
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        for i, (a, b) in enumerate(TWINS):
            ca = canon(semantic(REPO / a, Path(td) / f"{i}a.xml"))
            cb = canon(semantic(REPO / b, Path(td) / f"{i}b.xml"))
            if ca == cb:
                print(f"[equivalence] {Path(a).name} == {Path(b).name}: IDENTICAL")
            else:
                failures += 1
                print(f"[equivalence] {Path(a).name} != {Path(b).name}")
                for la, lb in zip(ca.splitlines(), cb.splitlines()):
                    if la != lb:
                        print(f"  UBL: {la.strip()}\n  CII: {lb.strip()}")
                        break
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

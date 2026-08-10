#!/usr/bin/env python3
"""faktorei · tools/render.py — development render pipeline.

Runs the two-phase transform (normalize -> semantic -> FO) with Saxon (XSLT 3.0
via saxonche) and formats the FO to PDF with Apache FOP. This mirrors exactly
what engine/ does in Java with Saxon-HE + embedded FOP; it exists so stylesheet
work never waits on an engine build.

Usage:
    python3 tools/render.py corpus/fixtures/ubl/001-base-multivat.xml out.pdf
    python3 tools/render.py input.xml out.pdf --lang de --param theme.accent='#1E4D3B'
    python3 tools/render.py input.xml out.fo --stop-at fo      # inspect the FO
    python3 tools/render.py input.xml out.xml --stop-at semantic

Requires: pip install saxonche · apt install fop
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NORMALIZERS = {
    "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2":
        REPO / "stylesheets/normalize/ubl-invoice.xsl",
    "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2":
        REPO / "stylesheets/normalize/ubl-creditnote.xsl",   # Phase 1 roadmap
    "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100":
        REPO / "stylesheets/normalize/cii.xsl",              # Phase 2 roadmap
}
RENDERER = REPO / "stylesheets/render/layout.xsl"


def detect_normalizer(xml_path: Path) -> Path:
    head = xml_path.read_text(encoding="utf-8", errors="replace")[:4000]
    for ns, xsl in NORMALIZERS.items():
        if ns in head:
            if not xsl.exists():
                sys.exit(f"error: input syntax recognised ({ns}) but its "
                         f"normalizer is not implemented yet: {xsl.name}")
            return xsl
    sys.exit("error: could not detect input syntax — no known document "
             "namespace found. Supported: UBL 2.1 Invoice/CreditNote, CII.")


def transform(executable, source: Path, dest: Path, params: dict[str, str]) -> None:
    from saxonche import PySaxonProcessor
    with PySaxonProcessor(license=False) as proc:
        xslt = proc.new_xslt30_processor()
        for k, v in params.items():
            xslt.set_parameter(k, proc.make_string_value(v))
        exe = xslt.compile_stylesheet(stylesheet_file=str(executable))
        exe_out = exe.transform_to_string(source_file=str(source))
        if exe_out is None:
            sys.exit(f"error: transform produced no output ({executable.name})")
        dest.write_text(exe_out, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--lang", default="en")
    ap.add_argument("--param", action="append", default=[],
                    metavar="NAME=VALUE", help="stylesheet parameter, repeatable")
    ap.add_argument("--stop-at", choices=["semantic", "fo", "pdf"], default="pdf")
    ap.add_argument("--pdfa", action="store_true",
                    help="PDF/A-3b profile: fop.xconf, embedded fonts (theme font "
                         "params switch to SourceSans3/SourceCodePro)")
    args = ap.parse_args()

    params = {"lang": args.lang}
    if args.pdfa:
        params.setdefault("theme.font-body", "SourceSans3")
        params.setdefault("theme.font-data", "SourceCodePro")
    for p in args.param:
        name, _, value = p.partition("=")
        params[name] = value

    normalizer = detect_normalizer(args.input)

    with tempfile.TemporaryDirectory() as td:
        semantic = Path(td) / "semantic.xml"
        transform(normalizer, args.input, semantic, {})
        if args.stop_at == "semantic":
            args.output.write_text(semantic.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"semantic model -> {args.output}")
            return

        fo = Path(td) / "doc.fo"
        transform(RENDERER, semantic, fo, params)
        if args.stop_at == "fo":
            args.output.write_text(fo.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"XSL-FO -> {args.output}")
            return

        cmd = ["fop", "-q"]
        if args.pdfa:
            cmd += ["-c", str(REPO / "infra/fop.xconf"), "-pdfprofile", "PDF/A-3b"]
        cmd += ["-fo", str(fo), "-pdf", str(args.output)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit("error: FOP formatting failed")
        print(f"PDF -> {args.output}")


if __name__ == "__main__":
    main()

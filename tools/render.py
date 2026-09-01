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
import shutil
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

        # Resolve FOP rather than exec'ing the bare name. On Windows the launcher
        # is fop.BAT: shutil.which() finds it, but CreateProcess will not run a
        # .BAT from a bare name without a shell, so subprocess raised a bare
        # FileNotFoundError — the FIRST command in the README, dying on a
        # traceback even though FOP was correctly installed. Resolving the path
        # makes Windows work; on Linux which() returns /usr/bin/fop and nothing
        # changes.
        fop_exe = shutil.which("fop")
        if fop_exe is None:
            sys.exit(
                "error: 'fop' was not found on PATH. Apache FOP formats the PDF: "
                "`sudo apt install fop` (Debian/Ubuntu), `brew install fop` (macOS), "
                "or https://xmlgraphics.apache.org/fop/. The stages before the PDF "
                "need no FOP — try --stop-at semantic or --stop-at fo. Or use "
                "ghcr.io/faktorei/render, which ships it."
            )
        cmd = [fop_exe, "-q"]
        if args.pdfa:
            # fop.xconf ships everywhere, but the OFL font files it points at are
            # not redistributed here — they are fetched, or come with the render
            # container. Without this check FOP fails deep in font resolution and
            # the error reads like a FOP bug rather than a missing asset.
            conf = REPO / "infra/fop.xconf"
            if not conf.is_file():
                sys.exit(f"error: --pdfa needs {conf}, which is missing.")
            missing = [f.name for f in (
                REPO / "fonts" / "SourceSans3-Regular.ttf",
                REPO / "fonts" / "SourceCodePro-Regular.ttf",
            ) if not f.is_file()]
            if missing:
                sys.exit(
                    "error: --pdfa embeds Source Sans 3 and Source Code Pro (SIL OFL-1.1), "
                    f"and fonts/ is missing {', '.join(missing)}. Those files are not "
                    "redistributed with the stylesheets — see NOTICE for a copy-paste "
                    "fetch, or use ghcr.io/faktorei/render, which ships them. Rendering "
                    "without --pdfa uses FOP's base-14 fonts and needs no fetch."
                )
            cmd += ["-c", str(conf), "-pdfprofile", "PDF/A-3b"]
        cmd += ["-fo", str(fo), "-pdf", str(args.output)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            sys.exit("error: FOP formatting failed")
        print(f"PDF -> {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""faktorei · tools/validate.py — CI gate 1: corpus validity against official rules.

Compiles the vendored official Schematron (CEN EN 16931 + Peppol layers) with
the vendored ISO skeleton, caches the compiled validators, runs documents
through them, and reports failed assertions from the SVRL.

Usage:
    python3 tools/validate.py corpus/fixtures/ubl/001-base-multivat.xml
    python3 tools/validate.py --all            # every fixture in the manifest
    python3 tools/validate.py FILE --warnings  # include warning-severity output

Exit codes: 0 clean (or warnings only), 1 fatal assertion failures, 2 setup error.

Prerequisite: python3 specwatch/pull.py  (vendors artefacts + skeleton)
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VENDOR = REPO / "specwatch" / "vendor"
SKELETON = VENDOR / "iso-schematron-skeleton" / "trunk" / "schematron" / "code"
CACHE = VENDOR / "compiled"

# Rule sets per profile, applied in order (CEN core first, then national layer).
PROFILES = {
    "peppol-bis-3-ubl": [
        VENDOR / "peppol-bis-billing/rules/sch/CEN-EN16931-UBL.sch",
        VENDOR / "peppol-bis-billing/rules/sch/PEPPOL-EN16931-UBL.sch",
    ],
    # Peppol BIS billing rules ship for UBL only; CII validates against the
    # CEN EN 16931 CII artefacts.
    "en16931-cii": [
        VENDOR / "en16931-artefacts/cii/schematron/EN16931-CII-validation.sch",
    ],
    # XRechnung = CEN EN 16931 core + the KoSIT BR-DE national layer. We use
    # the ConnectingEurope CEN artefacts (not Peppol's redistributed UBL copy)
    # so both syntaxes layer the same CEN base the KoSIT rules assume.
    "xrechnung-ubl": [
        VENDOR / "en16931-artefacts/ubl/schematron/EN16931-UBL-validation.sch",
        VENDOR / "xrechnung-schematron/src/validation/schematron/ubl/XRechnung-UBL-validation.sch",
    ],
    "xrechnung-cii": [
        VENDOR / "en16931-artefacts/cii/schematron/EN16931-CII-validation.sch",
        VENDOR / "xrechnung-schematron/src/validation/schematron/cii/XRechnung-CII-validation.sch",
    ],
    # PINT A-NZ does NOT layer on the CEN EN 16931 artefacts. It is a Peppol
    # International specialisation with its own two-layer stack: the PINT base
    # rules (preprocessed, so no code lists to resolve) then the A-NZ
    # jurisdiction layer. Mixing in the CEN layer would double-report and apply
    # EU rules (BR-CO-09's VAT-prefix requirement, for one) that PINT replaces.
    "pint-a-nz-ubl": [
        VENDOR / "pint-aunz-billing/trn-invoice/schematron/PINT-UBL-validation-preprocessed.sch",
        VENDOR / "pint-aunz-billing/trn-invoice/schematron/PINT-jurisdiction-aligned-rules.sch",
    ],
    "pint-a-nz-ubl-creditnote": [
        VENDOR / "pint-aunz-billing/trn-creditnote/schematron/PINT-UBL-validation-preprocessed.sch",
        VENDOR / "pint-aunz-billing/trn-creditnote/schematron/PINT-jurisdiction-aligned-rules.sch",
    ],
}

# corpus manifest (profile, syntax-family) -> validator profile above.
MANIFEST_PROFILES = {
    ("peppol-bis-3", "ubl"): "peppol-bis-3-ubl",
    ("en16931", "cii"): "en16931-cii",
    ("xrechnung", "ubl"): "xrechnung-ubl",
    ("xrechnung", "cii"): "xrechnung-cii",
    ("pint-a-nz", "ubl"): "pint-a-nz-ubl",
}

SVRL_NS = "http://purl.oclc.org/dsdl/svrl"


def compile_schematron(proc, xslt, sch: Path) -> Path:
    """ISO skeleton pipeline: dsdl-include -> abstract-expand -> svrl-for-xslt2.
    Compiled validators cached by content hash of the .sch."""
    digest = hashlib.sha256(sch.read_bytes()).hexdigest()[:16]
    cached = CACHE / f"{sch.stem}.{digest}.xsl"
    if cached.exists():
        return cached
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"[validate] compiling {sch.name} (one-time per artefact version)…")
    stage = sch
    for step in ("iso_dsdl_include.xsl", "iso_abstract_expand.xsl", "iso_svrl_for_xslt2.xsl"):
        exe = xslt.compile_stylesheet(stylesheet_file=str(SKELETON / step))
        out = exe.transform_to_string(source_file=str(stage))
        if out is None:
            sys.exit(f"error: skeleton step {step} produced no output for {sch.name}")
        tmp = CACHE / f".stage-{sch.stem}.xsl"
        tmp.write_text(out, encoding="utf-8")
        stage = tmp
    stage.rename(cached)
    return cached


def run_validator(proc, xslt, validator: Path, doc: Path) -> list[dict]:
    exe = xslt.compile_stylesheet(stylesheet_file=str(validator))
    svrl = exe.transform_to_string(source_file=str(doc))
    if svrl is None:
        sys.exit(f"error: validator {validator.name} produced no SVRL for {doc.name}")
    import xml.etree.ElementTree as ET
    root = ET.fromstring(svrl)
    failures = []
    for fa in root.iter(f"{{{SVRL_NS}}}failed-assert"):
        text_el = fa.find(f"{{{SVRL_NS}}}text")
        failures.append({
            "id": fa.get("id", ""),
            "flag": (fa.get("flag") or "fatal").lower(),
            "location": fa.get("location", ""),
            "text": " ".join((text_el.text or "").split()) if text_el is not None else "",
        })
    return failures


def validate(doc: Path, profile: str, show_warnings: bool) -> int:
    from saxonche import PySaxonProcessor
    fatal_count = 0
    with PySaxonProcessor(license=False) as proc:
        xslt = proc.new_xslt30_processor()
        for sch in PROFILES[profile]:
            if not sch.exists():
                sys.exit(f"error: artefact missing: {sch} — run specwatch/pull.py first")
            validator = compile_schematron(proc, xslt, sch)
            failures = run_validator(proc, xslt, validator, doc)
            fatals = [f for f in failures if f["flag"] == "fatal"]
            warns = [f for f in failures if f["flag"] != "fatal"]
            fatal_count += len(fatals)
            tag = sch.stem
            print(f"[validate] {doc.name} vs {tag}: "
                  f"{len(fatals)} fatal, {len(warns)} warning")
            for f in fatals + (warns if show_warnings else []):
                print(f"  [{f['flag'].upper()}] {f['id']}\n"
                      f"    at {f['location']}\n"
                      f"    {f['text']}")
    return fatal_count


# Schematron messages carry curly quotes and dashes. On a Windows console
# (cp1252) printing one raised UnicodeEncodeError and killed the validator
# mid-report — a failure became a crash, which is the wrong failure mode.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # already UTF-8, or not a reconfigurable stream


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", nargs="?", type=Path)
    ap.add_argument("--all", action="store_true",
                    help="validate every manifest fixture at its declared profile")
    ap.add_argument("--profile", default="peppol-bis-3-ubl", choices=PROFILES)
    ap.add_argument("--warnings", action="store_true")
    args = ap.parse_args()

    if args.all:
        import yaml
        manifest = yaml.safe_load((REPO / "corpus/manifest.yaml").read_text())
        jobs = []
        for fx in manifest["fixtures"]:
            family = "cii" if fx["syntax"] == "cii" else "ubl"
            key = (fx["profile"], family)
            if key not in MANIFEST_PROFILES:
                sys.exit(f"error: manifest fixture {fx['id']}: no validator "
                         f"profile for (profile={fx['profile']}, {family}) — "
                         f"add it to MANIFEST_PROFILES in validate.py")
            jobs.append((REPO / "corpus" / fx["file"], MANIFEST_PROFILES[key]))
    elif args.input:
        jobs = [(args.input, args.profile)]
    else:
        jobs = []
    if not jobs:
        sys.exit(2)

    total_fatal = sum(validate(d, prof, args.warnings) for d, prof in jobs)
    sys.exit(1 if total_fatal else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""faktorei · tools/visdiff.py — CI gate 4: visual regression.

Renders every manifest fixture (PDF/A profile, en), rasterizes at a fixed
DPI, and pixel-compares each page against the blessed baseline in
corpus/baselines/. Any unexpected delta fails. Baselines update ONLY via
--bless, which is an explicit, reviewed commit (plan §7).

Usage:
    python3 tools/visdiff.py            # compare against baselines
    python3 tools/visdiff.py --bless    # (re)write baselines from current output

Requires: pillow, poppler-utils. DPI pinned below — changing it re-blesses
the entire corpus by definition.

Sensitivity note (measured): at the pinned DPI, poppler's rasterization can
quantize away color deltas of ~2/255 in pale fills; text, layout, and any
visible color change register reliably (verified: 1-label change flags 11
pages). Do not rely on this gate for sub-JND color tuning.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from PIL import Image, ImageChops

REPO = Path(__file__).resolve().parent.parent
BASE = REPO / "corpus" / "baselines"
DPI = 110  # pinned; balance between diff sensitivity and repo weight


def raster_pages(pdf: Path, outdir: Path, stem: str) -> list[Path]:
    # Resolve rather than exec the bare name, and say so plainly when it is
    # absent: a missing rasterizer used to surface as a raw FileNotFoundError
    # from deep inside subprocess, which reads like a bug in this tool rather
    # than a missing dependency. (Windows also needs the resolved path when the
    # launcher is a .BAT/.EXE shim.)
    exe = shutil.which("pdftoppm")
    if exe is None:
        sys.exit(
            "error: 'pdftoppm' was not found on PATH. The pixel gate rasterizes "
            "PDFs with poppler: `sudo apt install poppler-utils` (Debian/Ubuntu), "
            "`brew install poppler` (macOS), or https://poppler.freedesktop.org/. "
            "Baselines are blessed in CI, so this gate is not required locally."
        )
    subprocess.run([exe, "-png", "-r", str(DPI), str(pdf), str(outdir / stem)],
                   check=True, capture_output=True)
    return sorted(outdir.glob(f"{stem}-*.png"))


def compare(a: Path, b: Path) -> int:
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if ia.size != ib.size:
        return -1
    diff = ImageChops.difference(ia, ib)
    bbox = diff.getbbox()
    if bbox is None:
        return 0
    # count differing pixels only within the changed region (fast path)
    region = diff.crop(bbox).convert("L")
    return sum(1 for v in region.tobytes() if v)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bless", action="store_true")
    ap.add_argument("--render-cmd", default=None,
                    help="alternate render command as a template with {src} and "
                         "{out} placeholders (e.g. the Java engine); defaults to "
                         "tools/render.py --pdfa. Lets the engine's parity gate "
                         "reuse this comparison against the same blessed baselines.")
    args = ap.parse_args()

    manifest = yaml.safe_load((REPO / "corpus/manifest.yaml").read_text())
    failures = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for fx in manifest["fixtures"]:
            fid, src = fx["id"], REPO / "corpus" / fx["file"]
            pdf = tmp / f"{fid}.pdf"
            if args.render_cmd:
                import shlex
                cmd = [a.replace("{src}", str(src)).replace("{out}", str(pdf))
                       for a in shlex.split(args.render_cmd)]
            else:
                cmd = [sys.executable, str(REPO / "tools/render.py"),
                       str(src), str(pdf), "--pdfa"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                print(f"[visdiff] {fid}: RENDER FAILED\n{r.stderr[-400:]}")
                failures += 1
                continue
            pages = raster_pages(pdf, tmp, fid)
            if "expected-pages" in fx and len(pages) != fx["expected-pages"]:
                print(f"[visdiff] {fid}: page count {len(pages)} != "
                      f"expected {fx['expected-pages']}")
                failures += 1
            for page in pages:
                baseline = BASE / page.name
                if args.bless:
                    BASE.mkdir(parents=True, exist_ok=True)
                    baseline.write_bytes(page.read_bytes())
                    continue
                if not baseline.exists():
                    print(f"[visdiff] {fid}: no baseline {baseline.name} — "
                          f"run --bless after review")
                    failures += 1
                    continue
                delta = compare(page, baseline)
                if delta:
                    out = REPO / f"visdiff-{page.name}"
                    out.write_bytes(page.read_bytes())
                    print(f"[visdiff] {fid}: {page.name} differs "
                          f"({'size mismatch' if delta < 0 else f'{delta} px'}) "
                          f"— current saved to {out.name}")
                    failures += 1
            if not args.bless:
                print(f"[visdiff] {fid}: {len(pages)} page(s) OK")
    if args.bless:
        print(f"[visdiff] baselines blessed into {BASE}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

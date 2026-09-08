#!/usr/bin/env python3
"""faktorei · tools/benchmark.py — throughput benchmark harness.

Runs `faktorei batch` over a benchmark corpus and emits a **machine-readable
result.json** (the methodology page renders from this artifact — no hand-
transcription, so re-runs are comparable and the transcription-error class is
gone) plus a human summary.

Protocol (defensible against hostile reproduction):
  * warm-up: one full pass over a subset (discarded) — "warm JVM" is the honest
    label; cold-start is a different number we don't publish as throughput.
  * throughput = documents / wall-clock (NOT the latency histogram); reported as
    the MEDIAN of N timed runs (median, not best — "best of N" is the tell), with
    min/max disclosed, normalized per core, plus a workers=1 single-core pass.
  * latency p50/p95/p99 reported alongside, clearly a DIFFERENT quantity.
  * veraPDF-3b confirmed on the run's output — "N/hour of conformant PDF/A-3b" is
    the claim; throughput of broken PDFs is free.
  * box descriptor + image are INPUT fields (not detect-and-guess).

    python3 tools/benchmark.py --corpus ./bench-corpus --engine <faktorei-engine>
        --workers 8 --box "Hetzner CCX23 (8 dedicated vCPU, 32GB)"
        --image ghcr.io/faktorei/render:2026.11.0 --image-digest sha256:… --out result.json

Publish only a result whose license_mode is "licensed" and verapdf.result "PASS".
Requires: pikepdf-free; veraPDF via ghcr.io/verapdf/cli (Docker).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Windows consoles default to cp1252, and these tools print party names and paths
# that carry non-ASCII — "Speicherstraße", an em dash, a curly quote. Printing one
# raised UnicodeEncodeError and killed the run: `--help` alone was enough to
# traceback. errors="replace" is correct HERE and would be wrong in gen_fixture.py
# / csv_to_jsonl.py, whose stdout IS the artifact — there a mangled character must
# crash rather than silently substitute.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # already UTF-8, or not a reconfigurable stream


def corpus_files(corpus: Path) -> list[Path]:
    return sorted(corpus.glob("*.xml"))


def corpus_sha256(files: list[Path]) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(f.read_bytes())
    return h.hexdigest()


def batch_cmd(engine: str, inp: Path, out: Path, workers: int) -> list[str]:
    return [engine, "batch", str(inp), str(out), "--workers", str(workers)]


def run_batch(engine: str, inp: Path, out: Path, workers: int, env: dict) -> tuple[float, dict, str]:
    """@return (wall_clock_s, report, license_mode)."""
    if out.exists():
        shutil.rmtree(out)
    t0 = time.perf_counter()
    p = subprocess.run(batch_cmd(engine, inp, out, workers), capture_output=True, text=True, env=env)
    wall = time.perf_counter() - t0
    rpt = out / "report.json"
    if not rpt.exists():
        # A failed batch (bad mount, license refusal, no docs) writes no report —
        # fail loudly with the engine's own stderr rather than limping to a
        # bogus throughput and a downstream KeyError.
        raise SystemExit(f"error: batch produced no report.json (engine exit {p.returncode}).\n"
                         f"--- engine stderr ---\n{(p.stderr or '').strip()[-1500:]}")
    report = json.loads(rpt.read_text())
    mode = "unknown"
    for line in (p.stderr or "").splitlines():
        if line.startswith("[license]"):
            mode = line.split()[1].lower()
            break
    if report.get("summary", {}).get("error", 1) or report.get("summary", {}).get("skipped", 1):
        print(f"  !! run had non-ok documents: {report.get('summary')}")
    return wall, report, mode


def pct(vals: list[float], p: float) -> float:
    if not vals:
        return 0.0
    k = (len(vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(vals) - 1)
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def verapdf_sample(pdf_dir: Path, sample: int) -> dict:
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        return {"profile": "3b", "sampled": 0, "passed": 0, "result": "SKIP"}
    chosen = pdfs[:: max(1, len(pdfs) // sample)][:sample] if len(pdfs) > sample else pdfs
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "sample"
        s.mkdir()
        for p in chosen:
            shutil.copy(p, s / p.name)
        mount = str(s.resolve())
        r = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{mount}:/data",
             "ghcr.io/verapdf/cli:latest", "--format", "text", "-f", "3b", "/data/"],
            capture_output=True, text=True)
        passed = r.stdout.count("PASS ")
        failed = r.stdout.count("FAIL ")
    return {"profile": "3b", "sampled": len(chosen), "passed": passed, "failed": failed,
            "result": "PASS" if failed == 0 and passed == len(chosen) else "FAIL"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--engine", required=True, help="path to the faktorei-engine launcher (or a wrapper)")
    ap.add_argument("--out", type=Path, default=Path("result.json"))
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=500)
    ap.add_argument("--seed", type=int, help="corpus seed (recorded for reproduction)")
    ap.add_argument("--image", default="dev-cli")
    ap.add_argument("--image-digest", default="")
    ap.add_argument("--box", default="dev (unspecified)")
    ap.add_argument("--license", type=Path, help="license file to mount (FAKTOREI_LICENSE)")
    ap.add_argument("--verapdf-sample", type=int, default=200)
    args = ap.parse_args()
    args.corpus = args.corpus.resolve()  # absolute: a relative path becomes a docker NAMED VOLUME, not a bind mount

    files = corpus_files(args.corpus)
    if not files:
        raise SystemExit(f"no .xml in {args.corpus}")
    m = len(files)
    env = {**os.environ}
    if args.license:
        # Fail HERE, not an hour later. Path.resolve() happily returns an absolute
        # path for a file that does not exist, and `docker -v <missing>:...` then
        # CREATES A DIRECTORY at that source path and bind-mounts it. The engine
        # finds a directory where faktorei.lic should be, reads no license, and runs
        # in evaluation mode — which is not an error, just an unpublishable result.
        # The failure is silent, costs a full run, and then poisons the retry: the
        # directory docker created is still sitting there, so a later
        # `scp bench.lic box:~/bench.lic` drops the file INSIDE it as
        # bench.lic/bench.lic and the next run fails the same way.
        lic = args.license.resolve()
        if lic.is_dir():
            raise SystemExit(
                f"error: --license is a DIRECTORY: {lic}\n"
                f"  Almost certainly created by an earlier run whose --license path did not\n"
                f"  exist (docker -v creates a directory for a missing bind source).\n"
                f"  Fix: rm -rf {lic}   then copy the real license file there.")
        if not lic.is_file():
            raise SystemExit(
                f"error: --license does not exist: {lic}\n"
                f"  Copy the .lic to this path first. Running without it would produce an\n"
                f"  evaluation-mode result that cannot be published.")
        env["FAKTOREI_LICENSE"] = str(lic)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # Warm-up: one full pass over a subset, discarded.
        warm = tmp / "warm-in"
        warm.mkdir()
        for f in files[: min(args.warmup, m)]:
            shutil.copy(f, warm / f.name)
        print(f"[bench] warm-up: {min(args.warmup, m)} docs (discarded)")
        run_batch(args.engine, warm, tmp / "warm-out", args.workers, env)

        # Single-core normalizer.
        print("[bench] single-core (workers=1) timed run")
        sc_wall, _, _ = run_batch(args.engine, args.corpus, tmp / "sc-out", 1, env)

        # N timed runs at --workers.
        walls, reports, mode = [], [], "unknown"
        for i in range(args.runs):
            out = tmp / f"run-{i}"
            wall, report, mode = run_batch(args.engine, args.corpus, out, args.workers, env)
            walls.append(wall)
            reports.append(report)
            print(f"[bench] run {i + 1}/{args.runs}: {wall:.2f}s  ({m / wall * 3600:,.0f} docs/hour)")
            if i < args.runs - 1:
                shutil.rmtree(out)  # keep only the last run's output (deterministic) for veraPDF
        last_out = tmp / f"run-{args.runs - 1}"

        median_wall = statistics.median(walls)
        median_report = reports[walls.index(sorted(walls)[len(walls) // 2])]
        durations = sorted(d["duration_ms"] for d in median_report["documents"] if d["status"] == "ok")

        vera = verapdf_sample(last_out, args.verapdf_sample)

        def per_hour(wall: float) -> float:
            return round(m / wall * 3600)

        result = {
            "throughput_docs_per_hour": {
                "median": per_hour(median_wall),
                "min": per_hour(max(walls)),
                "max": per_hour(min(walls)),
                "per_core_median": round(per_hour(median_wall) / args.workers),
            },
            "single_core_docs_per_hour": per_hour(sc_wall),
            "latency_ms": {"p50": round(pct(durations, 50), 1),
                           "p95": round(pct(durations, 95), 1),
                           "p99": round(pct(durations, 99), 1),
                           "note": "per-document render latency — a DIFFERENT quantity from throughput"},
            "corpus": {"count": m, "seed": args.seed, "sha256": corpus_sha256(files)},
            "image": {"tag": args.image, "digest": args.image_digest},
            "workers": args.workers,
            "cores_detected": os.cpu_count(),
            "box": args.box,
            "license_mode": mode,
            "verapdf": vera,
            "runs_wall_clock_s": [round(w, 3) for w in walls],
            "warmup_docs": min(args.warmup, m),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        args.out.write_text(json.dumps(result, indent=2))

    t = result["throughput_docs_per_hour"]
    print("\n=== faktorei benchmark ===")
    print(f"  throughput : {t['median']:,} docs/hour (median of {args.runs}; "
          f"{t['min']:,}–{t['max']:,}), {t['per_core_median']:,}/hour/core")
    print(f"  single-core: {result['single_core_docs_per_hour']:,} docs/hour")
    print(f"  latency    : p50 {result['latency_ms']['p50']}ms · p95 "
          f"{result['latency_ms']['p95']}ms · p99 {result['latency_ms']['p99']}ms")
    print(f"  conformance: veraPDF-3b {vera['result']} ({vera['passed']}/{vera['sampled']} sampled)")
    print(f"  license    : {mode}   corpus sha256 {result['corpus']['sha256'][:16]}…")
    print(f"  box        : {args.box}")
    print(f"  -> {args.out}")
    if mode != "licensed":
        print("  NOTE: license_mode is not 'licensed' — do NOT publish this run (watermark overhead / eval).")


if __name__ == "__main__":
    main()

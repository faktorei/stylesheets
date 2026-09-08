# faktorei render throughput — benchmark methodology

> **The claim we stand behind:** *N invoices/hour/core of conformant PDF/A-3b*,
> on a stated box, from a corpus anyone can regenerate and hash-verify.
>
> This page documents the method. The **published numbers are rendered from the
> machine-readable `result.json`** the harness emits — never hand-transcribed —
> so every figure on the page is traceable to one artifact and every re-run is
> directly comparable. If a number here disagrees with the linked `result.json`,
> the artifact wins.

Two files produce everything below, both in the public (Apache-2.0) `tools/`:

| tool | role |
|---|---|
| [`tools/gen_benchmark_corpus.py`](../tools/gen_benchmark_corpus.py) | deterministically generates the corpus from a published seed |
| [`tools/benchmark.py`](../tools/benchmark.py) | runs the protocol, emits `result.json` + a human summary |

The harness drives the shipped engine as a black box (`--engine <launcher>`), so
the measured artifact is the product, not a lab build.

---

## 1 · The corpus — distinct invoices, not one fixture N times

A reproducer's first question is *"did they benchmark a cache?"* So the corpus is
**10,000 distinct invoices**, each generated from `seed × 1,000,003 + index`.
Same seed → byte-identical corpus → identical `sha256`. The published seed is
**`42`**; regenerate and verify:

```sh
make bench-corpus                       # or: python3 tools/gen_benchmark_corpus.py --count 10000 --seed 42 --out <dir>
# prints:  sha256: <hash>   ← must match the hash in the published result.json
```

**Size** — 10,000 is large enough that warm-up amortizes to noise and small
enough to re-run cheaply and often.

### Mix — the honest shape of real traffic

Stated openly because it is the defensibility decision. It approximates real
invoice-size distribution (most invoices are short; utilities/bulk orders are the
long tail) and is **conservative against us** — an all-minimal corpus would render
faster and inflate the number.

| dimension | distribution |
|---|---|
| **lines** | 70 % small (1–5) · 25 % medium (10–40) · 5 % large (100–150) |
| **tax scenario** | 60 % standard @19 % · 20 % reduced @7 % · 15 % reverse-charge (AE) · 5 % zero-rated (Z) |
| **parties** | rotated across a pool of EU sellers/buyers (DE, SE, FR, NL, SK, BE, NO, IT, PL) |
| **text** | item descriptions include diacritics, guillemets, µ/Ω/×, and Cyrillic — the real glyph-coverage path, not ASCII-only |

Amounts derive from per-line quantity × unit price with internally consistent
totals, so every document renders clean (the benchmark measures rendering, and a
document that errored would be free throughput — excluded by construction).

> Language note: Slice A `batch` renders every document with one label language
> (`--lang`); per-document language is Slice C (manifest mode). Content-language
> variety above still exercises the full text/font path today; the published run
> states the label language used.

---

## 2 · The protocol

Run by [`tools/benchmark.py`](../tools/benchmark.py) — `make benchmark` with a
built engine, or drive the container launcher directly.

1. **Warm-up.** One full pass over a 500-doc subset, **discarded**. The published
   number is warm-JVM throughput — the honest label. Cold-start is a *different*
   number and we do not publish it as throughput.
2. **Throughput = documents ÷ wall-clock.** Not the latency histogram — that
   measures a different thing (§3). Reported as the **median of 5 timed runs**
   over the full 10,000, with **min/max disclosed**. Median, not best: *"best of
   N"* is exactly the tell a reproducer looks for.
3. **Per-core normalizer.** Workers = **physical cores**, and a separate
   **`workers=1`** pass is always run and reported. An *N/hour/core* claim is only
   honest if the single-core number is visible — otherwise the division is doing
   marketing work.
4. **Licensed, no watermark.** The published run is **licensed mode**: no eval
   watermark in the measured path (watermarking adds per-page overhead). Eval-mode
   throughput may appear as a footnote if it differs; it is a conservative lower
   bound, never the headline.
5. **Output to volume mode** — the bounded, real batch path (the ratified 100k
   path), not an in-memory zip.

### What is reported, exhaustively

Everything a skeptic needs to reproduce or challenge the number, all in
`result.json`:

- throughput (median, min–max, per-core) and the single-core figure
- p50 / p95 / p99 **latency**, explicitly labeled as latency (§3)
- corpus mix + **seed** + **sha256**
- image **tag + digest** (the exact artifact measured)
- **box descriptor** and worker count (+ cores detected)
- **veraPDF-3b pass confirmation on the run's own output** — because the claim is
  *conformant* PDF/A-3b; throughput of broken PDFs is worthless
- every run's wall-clock, warm-up size, and a UTC timestamp

---

## 3 · Throughput is not latency

Two different quantities, reported side by side and never conflated:

- **Throughput** — documents per hour of wall-clock across all workers. The
  business number ("this box clears my nightly run in X").
- **Latency** — per-document render time, p50/p95/p99. The tail is dominated by
  the 5 % large invoices; p99 is a large-document number, not the typical one.

Dividing throughput by latency is meaningless — concurrency is exactly the gap
between them.

---

## 4 · The reference box

Published numbers come from a **dedicated-vCPU** instance
(Hetzner CCX-class or equivalent), matching the deployment-guidance tier — **not**
a dev machine and **not** a shared-vCPU box (whose run-to-run variance would make
the figure unreproducible in either direction). The box descriptor is a **harness
input** (`--box "…"`), recorded verbatim in `result.json` — detect-and-guess would
be a second, silent source of error.

**Hardware variance — the number is host-bound.** Two instances of the *same*
dedicated-vCPU plan, measured days apart, differed by **+51% aggregate / +33%
single-core** on a byte-identical render path (see the two History rows) — cloud
dedicated-vCPU plans span CPU generations, and the physical die you land on dominates
the absolute figure more than anything in the software. So the invariants this
benchmark stands behind are the **methodology, the corpus `sha256`, the image digest,
and the veraPDF result**; the absolute throughput is hardware-bound. Size against
per-core measurements on **your own** hardware — the eval container and this harness
produce them in an evening. It also means a full 1/2/4/8-worker sweep must run on **one
box**: headline, per-core, and the scaling curve have to share a die to stay consistent.

---

## 5 · The result artifact

`result.json` is the single source of truth the methodology page renders from:

```json
{
  "throughput_docs_per_hour": { "median": 0, "min": 0, "max": 0, "per_core_median": 0 },
  "single_core_docs_per_hour": 0,
  "latency_ms": { "p50": 0, "p95": 0, "p99": 0, "note": "…render latency — a DIFFERENT quantity…" },
  "corpus": { "count": 10000, "seed": 42, "sha256": "…" },
  "image":  { "tag": "ghcr.io/…:2025.11.0", "digest": "sha256:…" },
  "workers": 8, "cores_detected": 8,
  "box": "Hetzner CCX23 (8 dedicated vCPU, 32 GB)",
  "license_mode": "licensed",
  "verapdf": { "profile": "3b", "sampled": 200, "passed": 200, "failed": 0, "result": "PASS" },
  "runs_wall_clock_s": [ … ], "warmup_docs": 500, "timestamp": "…Z"
}
```

**A run is publishable only if** `license_mode == "licensed"` **and**
`verapdf.result == "PASS"`. The harness prints a do-not-publish warning otherwise.

---

## 6 · Reproduce it yourself

`benchmark.py` drives an engine that answers `<engine> batch <in> <out> --workers
N`. To benchmark the *container* (not a local build), point `--engine` at the
adapter `tools/bench_container.sh`, which maps that call onto a `docker run` of the
digest-pinned image (corpus ro, output rw, license mounted, run as the calling
user). Set `FAKTOREI_IMAGE` to the digest.

```sh
chmod +x tools/bench_container.sh
export FAKTOREI_IMAGE=ghcr.io/faktorei/render@sha256:…   # digest-pinned, not the tag

# 1. regenerate the exact corpus and check the hash matches the published result.json
python3 tools/gen_benchmark_corpus.py --count 10000 --seed 42 --out ./bench-corpus

# 2. run the harness against the published image (licensed → no watermark)
python3 tools/benchmark.py \
    --corpus ./bench-corpus \
    --engine tools/bench_container.sh \
    --license ./faktorei.lic \
    --workers "$(nproc)" \
    --seed 42 \
    --image "ghcr.io/faktorei/render:<tag>" --image-digest "sha256:…" \
    --box "<your box, e.g. Hetzner CCX23 (8 dedicated vCPU, 32 GB)>" \
    --out result.json
```

Prove the wiring on a small corpus first (`--count 100 … --runs 1 --warmup 20`):
`result.json` must show `license_mode: "licensed"` and `verapdf.result: "PASS"`
before the full run counts. Your `corpus.sha256` must equal ours; throughput will
differ with hardware — that is the point of publishing the box and per-core number.

---

## 7 · Published result

*Transcribed from the machine-readable artifact
[`benchmark-results/2025.11.5.json`](benchmark-results/2025.11.5.json). This section
is hand-written markdown, so **if it and the artifact ever disagree, the artifact
wins** — and the always-current rendering is
[faktorei.dev/benchmark](https://faktorei.dev/benchmark), which interpolates every
figure from that JSON at build time. (This section previously claimed to be
generated and was not; it then drifted a full release behind. Naming the risk is
more honest than denying it.) Reproduce and compare via §6.*

| | |
|---|---|
| **Image** | `ghcr.io/faktorei/render:2025.11.5` · `sha256:815b89a9…` |
| **Box** | Linode Dedicated 8 GB — **4 dedicated vCPU**, eu-central (Frankfurt) |
| **Corpus** | 10,000 distinct invoices · seed `42` · sha256 `88e6c2d1…` |
| **Conformance** | licensed (no watermark) · **veraPDF-3b PASS** (200/200 sampled) · 2026-09-07 |

### 167,636 conformant PDF/A-3b invoices per hour

on **4 dedicated vCPU** — the median of 5 timed runs over the full 10,000-invoice
corpus (not best-of; range disclosed).

| metric | value |
|---|---|
| **Throughput** (median of 5) | **167,636 docs/hour** — min 164,738 · max 172,490 |
| Per core, sustained at full width | 41,909 docs/hour/core |
| Single core (`workers=1`) | 77,568 docs/hour |
| **Latency** p50 / p95 / p99 | 61 ms / 215 ms / 349 ms |

Per-run wall-clock over the 10k corpus: 208.7 / 218.5 / 217.1 / 214.8 / 211.7 s.
Latency is per-*document* render time — a different quantity from throughput (§3);
the p99 tail is dominated by the 5 % large invoices.

**This figure is 43% below the previous row, and that is the hardware.** We have now
measured three instances of the *same* "Dedicated 4 vCPU" plan and got three
different numbers — 194,347 (`2025.11.0`), 292,826 (`2025.11.1`), 167,636
(`2025.11.5`) — a 1.74× spread on a plan name. Unlike the earlier pair, this one is
*not* left as an inference: the software was ruled out directly by running the
`2025.11.1`, `.3` and `.5` images **on one identical host**, where all three landed
within ~3% of each other. So the `2025.11.2` render-path change (currency-aware
decimals, PINT A-NZ profile, GST labels) costs nothing measurable, and the earlier
row's open caveat — which explicitly refused to guess that change's direction or
size — is now answered rather than quietly dropped. All three rows stay published.
Size against per-core measurements on your own silicon (§4); the invariants worth
holding us to are the methodology, the corpus hash, the image digest and the veraPDF
result — *not* the absolute figure.

**The per-core number, read honestly.** Four cores deliver 168k/hour, but one core
alone does 78k/hour — so scaling is ~2.2×, not 4×. We publish both figures precisely
so an "N/hour/core" claim can't do quiet marketing work: **41,909/hour/core** is the
sustained rate with all four cores busy; **77,568** is what a single core does
uncontended.

### Where the scaling gap actually is (serial-fraction diagnosis)

The gap is a **serialized fraction of the render path**. Measured across 1/2/4/8
workers on this box, the speedup curve is **1.00× / 1.70× / 2.16× / 1.93×** — an
Amdahl fit at the peak puts the serial fraction near **~28%**, so the ceiling is
~3.5× no matter how many cores you add. The 8-worker point *regresses*: past the
core count more workers is contention, not speedup.

**Quote that fraction from the current artifact, not from memory — it moves with the
hardware.** We now have two *full* sweeps, each run on the box that produced its own
headline, with software that measures identical between them (§7 opening):

| | 1 → 2 → 4 → 8 workers | serial fraction | headline |
|---|---|---|---|
| `2025.11.1` box | 1.00× / 1.79× / 2.44× / 2.30× | ~21% | 292,826/h |
| `2025.11.5` box | 1.00× / 1.70× / 2.16× / 1.93× | ~28% | 167,636/h |

That is a like-for-like comparison — same corpus, same methodology, same render path
— so the gap between those two rows is **silicon**, and it moves the scaling story
as well as the absolute number. The slower box is also the *less* scalable one, and
its 8-worker point falls off harder. Never pair a curve from one row with a headline
from the other: they are only jointly meaningful when they come from one die.

What does carry across boxes is the diagnosis, because we chased the obvious suspects
rather than leave it a hand-wave:

- **It is *not* the synchronized Fop setup.** `FopFactoryHolder.newFop` is
  `synchronized` — but that lock exists to fix an observed FOP factory-setup race
  (concurrent setup corrupts a shared internal node cache), not for throughput.
  Replacing it with fully lock-free per-worker factories **leaves throughput
  unchanged** while reintroducing the race, so the lock is a correctness fix, not the
  bottleneck. (Guarded permanently by `FopFactoryHammerTest`.)
- **It is *not* GC.** ZGC changes nothing; ParallelGC buys ~10% (within run-to-run
  noise). The allocation rate isn't what's serializing us.

The residual lives inside the Saxon/FOP render internals themselves. Isolating and
lifting that specific hotspot is a **named post-launch optimization target** —
tracked, bounded, and honestly disclosed here rather than dressed up as headroom we
already understand. The headline number stands on its own measured merits; this is
the ceiling above it, diagnosed.

**The opening move, when we attack it.** The residual is owned by one (or a mix) of three
stages — the Saxon normalize/render transform, FOP's FO→layout, or PDF serialization.
Before optimizing anything, *attribute* it: one async-profiler run on the `batch` path
(workers = cores, this corpus) splits the serial time across the three and names the
owner. That's an evening's work and the first task of the post-launch effort — not
started now. A lock-free **per-worker-factory** refactor (it eliminates the FOP
setup race more robustly than the `newFop` lock, though on its own it does *not* move
throughput — verified) is parked on branch `experiment/per-worker-fop-factories` as
the concurrency foundation that work would build on.

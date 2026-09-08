#!/usr/bin/env bash
# faktorei · tools/bench_container.sh — adapter so tools/benchmark.py can drive the
# released *container* instead of a local CLI. benchmark.py invokes the engine as
#   <engine> batch <in> <out> --workers N
# with per-run temp dirs; this maps that onto a `docker run` of the image, mounts
# the corpus (ro), the output dir (rw), and the license, and runs as the calling
# user so the container can write report.json/PDFs the host (and benchmark.py) can
# read back. The container's `[license] …` line reaches benchmark.py via stderr, so
# license_mode is detected exactly as with the local CLI.
#
# Required env (benchmark.py passes its environment through):
#   FAKTOREI_IMAGE    digest-pinned image, e.g. ghcr.io/faktorei/render@sha256:…
#   FAKTOREI_LICENSE  host path to faktorei.lic (benchmark.py sets this from --license)
set -euo pipefail
: "${FAKTOREI_IMAGE:?set FAKTOREI_IMAGE to the digest-pinned faktorei/render image}"
: "${FAKTOREI_LICENSE:?set FAKTOREI_LICENSE (benchmark.py --license) to the host faktorei.lic}"

sub=$1; IN=$2; OUT=$3; shift 3   # remaining args (e.g. --workers N) pass straight through
# Absolute paths only: docker -v treats a relative source as a NAMED VOLUME, not a
# bind mount (-m tolerates OUT not existing yet — docker creates it).
IN=$(realpath -m "$IN"); OUT=$(realpath -m "$OUT")

# The license is the one mount that must ALREADY be a regular file. Unlike OUT,
# docker must not be allowed to invent it: for a missing bind source docker creates
# a DIRECTORY, mounts it at /lic/faktorei.lic, and the engine then reads no license
# and runs in evaluation mode — a silent, unpublishable result rather than an error.
# benchmark.py checks this too; the check is repeated here because this script is
# also driven by hand (docs/benchmark.md §6 tells customers to do exactly that).
FAKTOREI_LICENSE=$(realpath -m "$FAKTOREI_LICENSE")
if [ -d "$FAKTOREI_LICENSE" ]; then
  echo "bench_container: FAKTOREI_LICENSE is a DIRECTORY: $FAKTOREI_LICENSE" >&2
  echo "  docker created it for an earlier run whose license path did not exist." >&2
  echo "  Fix: rm -rf '$FAKTOREI_LICENSE' then copy the real .lic there." >&2
  exit 2
fi
if [ ! -f "$FAKTOREI_LICENSE" ]; then
  echo "bench_container: FAKTOREI_LICENSE does not exist: $FAKTOREI_LICENSE" >&2
  exit 2
fi
exec docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$IN":/in:ro \
  -v "$OUT":/out \
  -v "$FAKTOREI_LICENSE":/lic/faktorei.lic:ro \
  -e FAKTOREI_LICENSE=/lic/faktorei.lic \
  "$FAKTOREI_IMAGE" "$sub" /in /out "$@"

# Security policy

## Reporting a vulnerability

Email **security@faktorei.dev**. Please
include the input document (anonymised), the command or request, the image tag or
stylesheet commit, and what you observed. You will get a human reply within two
business days (Brisbane time) and a fix or a mitigation plan within 14 days for
anything that affects rendered output, document confidentiality, or the
container's isolation.

Do not open a public issue for a vulnerability until it is fixed; a public issue
is the right place for everything else.

## What is in scope

- These stylesheets and the Python tooling in this repository.
- The render container `ghcr.io/faktorei/render` (closed source; its behaviour is
  documented at https://faktorei.dev/docs). Of particular interest: any way a
  document can make the container read or write outside its working set, exhaust
  it with a small input, emit output that differs from a conformant render, or
  bypass the license and evaluation controls.

## What we already do

- Every input is bounded before any transform runs (document size, line count,
  batch size); hostile and malformed input must answer with a clean 4xx.
- The container runs as a non-root user on a read-only root filesystem, makes no
  outbound network connections, and logs nothing about document content.
- Images are digest-pinned, multi-arch, built from a pinned toolchain, and ship
  with SBOM and provenance attestations.
- Secret scanning and push protection are enabled on this repository.

Thank you for looking.

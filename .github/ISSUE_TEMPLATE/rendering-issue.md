---
name: Rendering issue
about: A document that renders wrong, ugly, or is refused — every report is corpus food
title: "[render] "
labels: rendering
---

<!--
A rendering issue is only actionable with a sample document. No sample, no repro.
ANONYMISE the sample: replace real party names, addresses, tax IDs, and line-item
text with fictional data — but keep the structure that triggers the problem.
-->

## Sample document (required)

Paste the minimal UBL or CII XML that reproduces the issue, or attach it:

```xml
<!-- your anonymised EN 16931 invoice here -->
```

## Syntax & profile

- [ ] UBL 2.1 Invoice
- [ ] UBL 2.1 CreditNote
- [ ] CII (Cross Industry Invoice, D16B)
- Profile: <!-- Peppol BIS 3.0 / XRechnung / Factur-X / plain EN 16931 -->

## Expected vs. actual

**Expected:** <!-- what the rendered PDF should show -->

**Actual:** <!-- what it shows instead; a screenshot or the produced PDF helps -->

## Environment

- How rendered: <!-- tools/render.py in this repo / the ghcr.io/faktorei/render container / other -->
- Command: <!-- e.g. python3 tools/render.py sample.xml out.pdf --lang de -->

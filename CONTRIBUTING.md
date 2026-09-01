# Contributing to Faktorei stylesheets

Thank you for helping render the world's e-invoices correctly.

## The contribution we want most: a fixture that breaks a renderer

Real invoices are stranger than specs. If you have an EN 16931 document (UBL or
CII) whose layout, glyph coverage, VAT breakdown, or national profile we render
wrong — or refuse — that is the highest-value thing you can send. Every such
report becomes a permanent corpus fixture and a regression test.

### Adding a fixture

1. **Anonymise it.** Replace real party names, addresses, tax IDs, and line-item
   descriptions with fictional data. Keep the *structure* that triggers the bug.
   (Our own fixtures trade as "Nordkontor Supplies GmbH" — invent your own.)
2. Drop the file under `corpus/fixtures/ubl/` or `corpus/fixtures/cii/` with the
   next free number and a descriptive slug (e.g. `021-multi-page-allowances.xml`;
   check `corpus/manifest.yaml` for the highest number in use).
3. Register it in `corpus/manifest.yaml` with its validation `profile`.
4. Run the local checks (below) and open a PR describing expected vs. actual.

### Local checks (Definition of Done)

```sh
pip install saxonche pyyaml && sudo apt install fop
python3 specwatch/pull.py                        # vendor official artefacts
python3 tools/validate.py --all                  # must be 0-fatal / 0-warning
python3 tools/render.py <your-fixture> out.pdf   # must produce a PDF

# The contract gates. CI runs these on your PR, so run them first:
python3 tools/test_equivalence.py                # UBL/CII twins normalize identically
python3 tools/test_money.py                      # decimals per currency, separators per language
python3 tools/test_profile.py                    # profile deltas apply and stay scoped
```

`--pdfa` (embedded-font PDF/A-3b) additionally needs the OFL fonts, which are not
redistributed here — see [NOTICE](NOTICE) for a copy-paste fetch. Plain
`tools/render.py` uses FOP's base-14 fonts and needs nothing extra.

Visual-regression baselines (`corpus/baselines/`) and the pixel-diff gate are
maintained in the private monorepo, where the full toolchain (embedded fonts,
PDF/A profile) lives — you do **not** need to bless baselines in your PR.

## How changes actually land (asymmetric, stated plainly)

This repository is a **one-way public mirror** of the Apache-2.0 subset of a
private monorepo, where the complete CI gate stack runs and where changes are
integrated. So the flow is:

> Your PR opens here → a maintainer reviews it and applies it in the monorepo
> (full gates: official validation, render, visual regression, determinism) →
> it lands there → the next sync mirrors it back → your PR is closed with a
> reference to the sync commit.

The private monorepo is where CI truth lives; your change ships in the next sync.
This is honest about the open-core split and keeps the public history clean.

## Contributor License Agreement

Contributions require agreeing to the lightweight [CLA](CLA.md) — confirm it with
the checkbox in the pull-request template. It lets us keep the project
Apache-2.0-licensed and relicense-safe without chasing signatures later.

## Code of conduct

Be kind and technical. Assume good faith. We are here to render invoices.

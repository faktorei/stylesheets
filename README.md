# Faktorei — EN 16931 e-invoice rendering stylesheets

Open-source XSLT 3.0 / XSL-FO stylesheets that turn EN 16931 electronic invoices
(Peppol BIS Billing 3.0, XRechnung, and the Factur-X/ZUGFeRD CII profile) into
clean, print-ready PDF — validated 0-fatal/0-warning against the **official**
CEN and OpenPeppol Schematron, and tracked to the semi-annual spec cycle.

![Specimen — an EN 16931 UBL invoice rendered by Faktorei](corpus/baselines/001-1.png)

*Above: `corpus/fixtures/ubl/001-base-multivat.xml` rendered by the stylesheets in
this repo. Every PNG under `corpus/baselines/` is a blessed render of a corpus fixture.*

## How it works — one renderer, every syntax

A two-phase transform is the load-bearing decision:

```
UBL 2.1 ─┐
CII ─────┼─ normalize/*.xsl ──► semantic model ──► render/layout.xsl ──► XSL-FO ──► FOP ──► PDF
         │                     (EN 16931 BT-/BG-,       + blocks/*                (Apache FOP)
(syntax) ┘                      urn:faktorei:semantic)     + themes/*  + i18n/*
```

Normalizers map each input syntax onto **one** semantic vocabulary
(`stylesheets/semantic/model.md`); the renderer consumes only that. National
profiles (XRechnung, etc.) are configuration deltas, not forks. Styling lives
exclusively in theme attribute-sets — the contract is the header of
`stylesheets/render/themes/ledger.xsl`; the public parameter surface is
`stylesheets/config/params.md`.

**Shipped today:** two label locales — **English and German** — and the **Ledger**
theme (the default; further themes are in development). Additional locales (French,
Dutch) are on the roadmap, not yet shipped.

## Quickstart

```sh
pip install saxonche pyyaml            # Saxon-HE 12 (XSLT 3.0) + manifest parsing
sudo apt install fop                   # Apache FOP (Debian/Ubuntu); brew install fop on macOS

# Render a fixture to PDF (base-14 fonts, no setup):
python3 tools/render.py corpus/fixtures/ubl/001-base-multivat.xml out.pdf
python3 tools/render.py corpus/fixtures/ubl/001-base-multivat.xml de.pdf --lang de

# Inspect the intermediate stages:
python3 tools/render.py corpus/fixtures/ubl/001-base-multivat.xml sem.xml --stop-at semantic
python3 tools/render.py corpus/fixtures/ubl/001-base-multivat.xml doc.fo  --stop-at fo
```

`tools/render.py` is the reference pipeline. The quickstart renders with FOP's
base-14 fonts so it works with nothing but this repo. **Embedded-font PDF/A-3b**
(the production profile — Source Sans 3 / Source Code Pro, SIL OFL) needs those
fonts fetched locally, or simply use the container below, which ships them.

## Validate against the official artefacts

```sh
python3 specwatch/pull.py              # vendor the pinned official Schematron (network)
python3 tools/validate.py --all        # every fixture, official CEN + Peppol + KoSIT rules
```

The pins live in `specwatch/sources.yaml` (OpenPeppol, CEN, KoSIT, ISO skeleton),
each at a release tag; `specwatch/lock.json` records the exact artefacts. This is
the credibility claim you can reproduce: **the corpus validates clean against the
same rules a real Access Point applies.**

## The rendered product, as a container

For production — deterministic **PDF/A-3b** with embedded fonts, Factur-X hybrid
packaging, an HTTP service, and batch — the render engine ships as a container:

```sh
docker run -p 8080:8080 ghcr.io/faktorei/render:2025.11
curl -X POST --data-binary @corpus/fixtures/ubl/001-base-multivat.xml localhost:8080/render -o out.pdf
```

**Open-core, stated plainly:** these stylesheets (the rendering logic, the corpus,
the validation machinery) are Apache-2.0 and are the whole story of *how* the PDF
is produced. The container is the commercial packaging of that logic — the
byte-deterministic PDF/A engine, licensing, and operational surface. What renders
your invoice is open; what you pay for is not having to operate it.

More at **[faktorei.dev](https://faktorei.dev)**.

## Contributing

The most valuable contribution is a **fixture that breaks a renderer** — a real
(anonymized) invoice whose layout, glyph coverage, or profile we don't yet handle.
See [CONTRIBUTING.md](CONTRIBUTING.md). Note the workflow is asymmetric and honest:
the private monorepo is where the full CI gate stack runs and where changes land;
your PR here is reviewed, applied upstream, and mirrored back in the next sync.

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Contributions require the
lightweight [CLA](CLA.md).

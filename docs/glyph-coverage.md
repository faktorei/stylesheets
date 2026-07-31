# Glyph coverage — fail loud, never tofu

faktorei's embedded fonts (Source Sans 3 for text, Source Code Pro for data) cover
**Latin, Latin Extended, Greek, and Cyrillic** — the scripts EN 16931 invoicing
across the EU needs. They do **not** cover CJK (Chinese/Japanese/Korean) or other
scripts outside that range.

## The policy

When a document contains a **content** character the embedded fonts can't
render, the engine **refuses the document** with a clear error naming the missing
code points and the font:

```
error: glyph coverage — the document uses characters not in the embedded fonts:
U+6E2C '測' (font SourceSans3-Regular), … ; faktorei refuses rather than emit
unreadable output
```

It does **not** silently substitute tofu (□□□). A rendering-infrastructure
product that emits unreadable boxes onto a **legal document** is worse than one
that refuses: the refusal is visible and actionable; the tofu invoice looks fine
until a tax authority or a customer can't read it.

Precision: the check fires only on real content glyphs. Benign zero-width
formatting characters (soft hyphen, zero-width space/joiners) that render fine are
ignored, and normal international content — German/French diacritics, Cyrillic,
Greek — renders unaffected (regression-tested in `GlyphCoverageTest`).

## There is no opt-out — and why you don't need one

There is deliberately **no `FAKTOREI_ALLOW_TOFU` flag.** The objection — *"but my
billing run of 100,000 invoices can't fail because one has an unrenderable
character"* — is already answered by how batch works:

**Batch is skip-and-continue with per-document error reporting.** One product name
with a CJK character fails **that one document** into `report.json` with the glyph
coverage error, while the other 99,999 complete and are written normally. The bad
document is isolated, named, and reportable; nothing else is blocked.

**Failure isolation is the escape hatch.** A `FAKTOREI_ALLOW_TOFU` flag would exist
for exactly one purpose: to let someone knowingly ship a broken legal document
with unreadable content. That is not a capability we offer. If you need CJK, the
answer is CJK *fonts*, not a switch that degrades the output.

## The path for CJK

CJK support is a **documented optional add-on**, not default baggage — a Noto CJK
font is 15–100 MB, an image-size decision we don't impose on the 99% of EU
invoicing that never needs it. A future optional font layer (mount or image
variant) that adds Noto CJK to the embedded set would let these documents render;
until then, they are refused rather than mangled.

The policy is asserted by `corpus/fixtures/policy/016-cjk.xml` (a *policy* fixture
— it lives outside the render-globbed `ubl/`/`cii/` dirs and is not in the
visual/validation manifest, precisely because it is meant to be refused, not
rendered) via `GlyphCoverageTest` and the engine.yml CJK-refusal gate.

> The reference `tools/render.py` is a development pipeline and does not enforce
> this policy (it leaves FOP's default warn-and-tofu behavior); the guarantee is a
> property of the **engine**, the licensed product surface.

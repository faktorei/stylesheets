# Public parameter surface

These parameters are stable API. Anything not listed here (template names,
internal modes) may change between releases without notice; the exception is
theme attribute-set names, which are stable per themes/ledger.xsl.

| Parameter | Default | Purpose |
|---|---|---|
| `lang` | `en` | Label bundle: `i18n/labels-{lang}.xml`. Shipped: en, de. Also selects decimal formatting convention. |
| `logo-uri` | `''` | Image placed top-left (file URI or data: URI). When empty, the seller name renders in its place. |
| `profile` | `auto` | Presentation profile: `auto` \| `generic` \| `xrechnung` \| `pint-a-nz`. `auto` derives from the document's BT-24 CustomizationID (any KoSIT/XRechnung URN → `xrechnung`; a PINT A-NZ URN, i.e. one containing `@aunz` → `pint-a-nz`; else `generic`). `xrechnung`: BT-10 is labeled "Leitweg-ID" and accented in the meta strip (never falls back to the order reference), and the seller contact person + phone (BR-DE-5/6/7) are shown. `pint-a-nz`: the tax is labeled **GST** rather than VAT (Australia/New Zealand wording), via the profile-scoped label override described below. Forcing a profile on a document of another kind relabels it accordingly. |
| `theme.accent` | `#2A4B8D` | Brand accent (payment details, highlights). |
| `theme.ink` | `#22252B` | Primary text color. |
| `theme.ink-soft` | `#5A5F68` | Secondary text color. |
| `theme.zebra` | `#F1F4F0` | Even-row tint in the line table. |
| `theme.rule` | `#22252B` | Structural rule color. |
| `theme.font-body` | `Helvetica` | Body face. Production: register real fonts in fop.xconf and set here. |
| `theme.font-data` | `Helvetica` | Amounts/identifiers face. Production: a tabular-numeral mono (IBM Plex Mono). |

Custom themes: import `themes/ledger.xsl`, override attribute-sets. See the
theming contract in that file's header.

## Profile-scoped labels

Any label key may carry a `@<profile>` suffix in `i18n/labels-{lang}.xml`, and that entry wins
over the bare key when the resolved profile matches:

```xml
<label key="totals.vat">Total VAT</label>
<label key="totals.vat@pint-a-nz">Total GST</label>
```

This exists because some wording is a **jurisdiction** property rather than a language one.
PINT A-NZ calls the tax GST, but an English-language European invoice must still say VAT — so a
per-region label bundle would be the wrong shape and would corrupt every other profile sharing
that language. Profiles that declare no override fall through to the bare key unchanged.

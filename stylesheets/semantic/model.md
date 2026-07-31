# faktorei semantic model (`urn:faktorei:semantic:invoice:1`)

The internal pivot vocabulary between syntax normalizers and the renderer,
mirroring the EN 16931 semantic data model. Every element carries a `bt=""`
attribute naming the business term it represents, so any field in a rendered
PDF is traceable to the standard (and to the official UBL/CII mapping tables,
which are the implementation guide for normalizers).

## Contract rules

1. Normalizers emit this vocabulary; the renderer consumes only this
   vocabulary. Neither side ever sees the other's syntax.
2. Optional business terms are *omitted*, never emitted empty. The renderer
   treats absence as "suppress the block" — no blank labeled rows, ever.
3. Amounts are copied verbatim as decimal strings (no arithmetic in
   normalizers); formatting is exclusively a renderer concern.
4. Additions to the vocabulary are backwards-compatible (new elements only);
   renames/removals are a major-version event.

Normalizers implemented: UBL 2.1 Invoice, UBL 2.1 CreditNote, CII (D16B).
Equivalence contract enforced by tools/test_equivalence.py.

## Currently mapped (starter scope)

| Group | Terms |
|---|---|
| Document | BT-1, BT-2, BT-5, BT-9, BT-10, BT-13, BT-22, type code, CustomizationID/ProfileID |
| Seller (BG-4) | name, endpoint, VAT ID, legal ID, address (BG-5), contact (BG-6) |
| Buyer (BG-7) | name, endpoint, VAT ID, address (BG-8) |
| Payment (BG-16/17) | BT-81, BT-83, BT-84, BT-85, payment terms BT-20 |
| Lines (BG-25) | BT-126, BT-129, BT-131, BT-146, BT-153, BT-154, line VAT (BG-30) |
| VAT breakdown (BG-23) | BT-116, BT-117, BT-118/119 (as @cat/@rate), BT-120 |
| Doc allowances/charges (BG-20/21) | kind, reason (BT-97/98/104/105), amount (BT-92/99), VAT (BT-95/96/102/103) |
| Totals (BG-22) | BT-106..BT-110, BT-112, BT-113, rounding BT-114, BT-115 (BT-111 VAT-in-accounting-currency: roadmap) |

## Roadmap (in mapping-table order of pain)

Delivery information (BG-13..15),
payee/tax representative (BG-10/11), preceding invoice references (BG-3),
attachments (BG-24), item attributes and classification (BT-157..160),
line-level allowances/charges (BG-27/28), line period (BG-26), payment card /
direct debit (BG-18/19), invoicing period (BG-14), multiple PaymentMeans.

#!/usr/bin/env python3
"""faktorei · tools/gen_fixture.py — deterministic high-line-count fixture generator.

Note: the emitted "<!-- kontor corpus fixture -->" comment and the "Nordkontor"
party are intentionally NOT rebranded — they are test-data output that must stay
byte-identical to the committed corpus fixtures (e.g. 017), which the kontor→
faktorei rename left exempt. Change them and the committed fixtures stop
round-tripping through this generator.

Emits a Peppol BIS-shaped UBL invoice with N lines and internally consistent
arithmetic (line nets exact to 2dp; category taxable = sum of its lines; VAT
rounded half-up; document totals derived). Seeded PRNG: same N -> same bytes,
so generated fixtures are corpus-stable.

Usage: python3 tools/gen_fixture.py 120 > corpus/fixtures/ubl/003-lines-120.xml
"""
import random
import sys
from decimal import Decimal, ROUND_HALF_UP

N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
rng = random.Random(N)  # seed by N: deterministic per size
C2 = Decimal("0.01")

ITEMS = [
    ("Pallet cage 1200×800", "Galvanised steel, stackable", Decimal("89.50"), 19),
    ("Transport crate PP-60", "Polypropylene, 60 L", Decimal("86.50"), 19),
    ("Packing paper roll", "Recycled kraft, 90 g/m²", Decimal("1.36"), 7),
    ("Stretch film 500mm", "23 µm, transparent", Decimal("4.85"), 19),
    ("Edge protector 1200mm", "Solid board, 35×35", Decimal("0.62"), 19),
    ("Label sheet A4", "Removable adhesive, 24-up", Decimal("0.19"), 7),
    ("Strapping band PET", "16 mm × 0.8 mm, green", Decimal("38.20"), 19),
    ("Container seal", "Numbered, tamper-evident", Decimal("1.05"), 19),
]

lines, cat_taxable = [], {}
for i in range(1, N + 1):
    name, desc, price, rate = ITEMS[rng.randrange(len(ITEMS))]
    qty = rng.randint(1, 40)
    net = (price * qty).quantize(C2)
    cat_taxable[rate] = cat_taxable.get(rate, Decimal("0")) + net
    lines.append((i, name, desc, qty, price, net, rate))

cat_tax = {r: (t * r / 100).quantize(C2, ROUND_HALF_UP) for r, t in cat_taxable.items()}
line_total = sum(l[5] for l in lines)
vat_total = sum(cat_tax.values())
gross = line_total + vat_total

def line_xml(i, name, desc, qty, price, net, rate):
    return f"""  <cac:InvoiceLine>
    <cbc:ID>{i}</cbc:ID>
    <cbc:InvoicedQuantity unitCode="C62">{qty}</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">{net}</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Description>{desc}</cbc:Description>
      <cbc:Name>{name}</cbc:Name>
      <cac:ClassifiedTaxCategory>
        <cbc:ID>S</cbc:ID>
        <cbc:Percent>{rate}</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:ClassifiedTaxCategory>
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">{price}</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>"""

subtotals = "\n".join(f"""    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">{cat_taxable[r]}</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">{cat_tax[r]}</cbc:TaxAmount>
      <cac:TaxCategory>
        <cbc:ID>S</cbc:ID>
        <cbc:Percent>{r}</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>""" for r in sorted(cat_taxable, reverse=True))

print(f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- kontor corpus fixture: generated, {N} lines (tools/gen_fixture.py {N}).
     Exercises: multi-page pagination, repeating header, carry-forward totals. -->
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
  <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
  <cbc:ID>KTR-2026-L{N}</cbc:ID>
  <cbc:IssueDate>2026-07-01</cbc:IssueDate>
  <cbc:DueDate>2026-07-31</cbc:DueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cbc:BuyerReference>PO-BULK-{N}</cbc:BuyerReference>
  <cac:AccountingSupplierParty>
    <cac:Party>
      <cbc:EndpointID schemeID="0088">7300010000001</cbc:EndpointID>
      <cac:PartyName><cbc:Name>Nordkontor Supplies GmbH</cbc:Name></cac:PartyName>
      <cac:PostalAddress>
        <cbc:StreetName>Speicherstraße 14</cbc:StreetName>
        <cbc:CityName>Hamburg</cbc:CityName>
        <cbc:PostalZone>20457</cbc:PostalZone>
        <cac:Country><cbc:IdentificationCode>DE</cbc:IdentificationCode></cac:Country>
      </cac:PostalAddress>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>DE812345678</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Nordkontor Supplies GmbH</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty>
    <cac:Party>
      <cbc:EndpointID schemeID="0106">54312780</cbc:EndpointID>
      <cac:PartyName><cbc:Name>Van der Meer Logistiek B.V.</cbc:Name></cac:PartyName>
      <cac:PostalAddress>
        <cbc:StreetName>Havenkade 220</cbc:StreetName>
        <cbc:CityName>Rotterdam</cbc:CityName>
        <cbc:PostalZone>3011 XN</cbc:PostalZone>
        <cac:Country><cbc:IdentificationCode>NL</cbc:IdentificationCode></cac:Country>
      </cac:PostalAddress>
      <cac:PartyTaxScheme>
        <cbc:CompanyID>NL861234567B01</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>
      </cac:PartyTaxScheme>
      <cac:PartyLegalEntity>
        <cbc:RegistrationName>Van der Meer Logistiek B.V.</cbc:RegistrationName>
      </cac:PartyLegalEntity>
    </cac:Party>
  </cac:AccountingCustomerParty>
  <cac:PaymentMeans>
    <cbc:PaymentMeansCode>30</cbc:PaymentMeansCode>
    <cbc:PaymentID>KTR-2026-L{N}</cbc:PaymentID>
    <cac:PayeeFinancialAccount>
      <cbc:ID>DE89370400440532013000</cbc:ID>
    </cac:PayeeFinancialAccount>
  </cac:PaymentMeans>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">{vat_total}</cbc:TaxAmount>
{subtotals}
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">{line_total}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">{line_total}</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">{gross}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">{gross}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
{chr(10).join(line_xml(*l) for l in lines)}
</Invoice>""")

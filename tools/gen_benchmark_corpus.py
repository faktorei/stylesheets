#!/usr/bin/env python3
"""faktorei · tools/gen_benchmark_corpus.py — deterministic benchmark corpus.

REPRODUCIBILITY CONTRACT — do NOT change the emitted bytes: this generator's
output hash (seed 42 → sha256) is PUBLISHED in the benchmark results
(docs/benchmark-results/*.json, benchmark.md §7). Altering the party pool,
templates, mix, or ordering silently invalidates that published hash while every
CI gate stays green. Freeze the output; version a new corpus rather than mutate
this one. (This is why the kontor→faktorei rename deliberately left the test-data
party "Nordkontor Supplies GmbH" untouched here.)

Emits M **distinct** Peppol BIS-shaped UBL invoices (never one fixture N times —
a reproducer's first check is whether the number is a cache hit), generated
deterministically from a published integer seed so anyone can regenerate the
exact corpus and verify the hash. The mix approximates real invoice traffic and
is conservative against us (an all-minimal corpus would render faster):

    line count : 70% small (1–5) · 25% medium (10–40) · 5% large (100–150)
    tax scenario: 60% S@19 · 20% S@7 · 15% AE (reverse charge) · 5% Z (zero-rated)

Parties, items (incl. diacritics/Cyrillic), quantities and amounts vary across
the corpus; arithmetic is internally consistent (renders clean, no Schematron
dependency). Publish the seed + this mix table + the printed corpus sha256 in the
methodology.

    python3 tools/gen_benchmark_corpus.py --count 10000 --seed 42 --out ./bench-corpus
"""
from __future__ import annotations

import argparse
import hashlib
import random
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Windows consoles default to cp1252, and these tools print party names and paths
# that carry non-ASCII — "Speicherstraße", an em dash, a curly quote. Printing one
# raised UnicodeEncodeError and killed the run: `--help` alone was enough to
# traceback. errors="replace" is correct HERE and would be wrong in gen_fixture.py
# / csv_to_jsonl.py, whose stdout IS the artifact — there a mangled character must
# crash rather than silently substitute.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # already UTF-8, or not a reconfigurable stream

C2 = Decimal("0.01")

# (name, street, city, zip, cc, vatid, endpoint-scheme, endpoint)
SELLERS = [
    ("Nordkontor Supplies GmbH", "Speicherstraße 14", "Hamburg", "20457", "DE", "DE812345678", "0088", "7300010000001"),
    ("Ångström Mätteknik AB", "Verkstadsgatan 3", "Göteborg", "41764", "SE", "SE556123456701", "0088", "7350010000009"),
    ("Lemaître Outillage SAS", "18 rue des Fabriques", "Lyon", "69003", "FR", "FR40391838042", "0009", "39982600000019"),
    ("Van der Meer Techniek B.V.", "Havenkade 220", "Rotterdam", "3011 XN", "NL", "NL861234567B01", "0106", "54312780"),
    ("Kováč Náradie s.r.o.", "Priemyselná 7", "Košice", "04001", "SK", "SK2020123456", "0088", "8580000000002"),
]
BUYERS = [
    ("Baumann Meßtechnik GmbH", "Königsallee 42", "Düsseldorf", "40212", "DE", "DE998877665"),
    ("Peeters Logistiek NV", "Vaartstraat 9", "Antwerpen", "2000", "BE", "BE0123456789"),
    ("Grønnbygg AS", "Havnegata 11", "Bergen", "5004", "NO", "NO987654321MVA"),
    ("Rossi Imballaggi S.r.l.", "Via Meucci 20", "Bologna", "40138", "IT", "IT01234567890"),
    ("Nowak Opakowania Sp. z o.o.", "ul. Fabryczna 5", "Wrocław", "50-001", "PL", "PL1234567890"),
    ("Åberg Verktyg AB", "Industrigatan 8", "Malmö", "21120", "SE", "SE556987654301"),
]
# (name, description, unit price, unit code)
ITEMS = [
    ("Pallet cage 1200×800", "Galvanised steel, EN 10346, stackable", Decimal("89.50"), "C62"),
    ("Transport crate PP-60", "Polypropylene, 60 L, food-safe", Decimal("86.50"), "C62"),
    ("Packing paper roll", "Recycled kraft, 90 g/m²", Decimal("1.36"), "KGM"),
    ("Stretch film 500 mm", "23 µm, transparent", Decimal("4.85"), "C62"),
    ("Kalibrierschlüssel »Ω-Reihe«", "Präzision nach DIN, ±0,02 mm", Decimal("120.00"), "C62"),
    ("Calibre étalon «Mesure»", "Acier trempé, certificat d'étalonnage", Decimal("340.50"), "C62"),
    ("Калибр образцовый K-3", "Эталонный инструмент, класс 0,5", Decimal("12.30"), "C62"),
    ("Strapping band PET", "16 mm × 0.8 mm", Decimal("38.20"), "C62"),
    ("Container seal", "Numbered, tamper-evident", Decimal("1.05"), "C62"),
    ("Edge protector 1200 mm", "Solid board, 35×35", Decimal("0.62"), "C62"),
]
# (category, rate, weight, exemption-reason-or-None)
SCENARIOS = [
    ("S", 19, 0.60, None),
    ("S", 7, 0.20, None),
    ("AE", 0, 0.15, "Reverse charge — VAT to be accounted for by the recipient (Art. 196 Directive 2006/112/EC)"),
    ("Z", 0, 0.05, None),
]


def pick_lines(rng: random.Random) -> int:
    r = rng.random()
    if r < 0.70:
        return rng.randint(1, 5)
    if r < 0.95:
        return rng.randint(10, 40)
    return rng.randint(100, 150)


def pick_scenario(rng: random.Random):
    r, acc = rng.random(), 0.0
    for cat, rate, w, reason in SCENARIOS:
        acc += w
        if r < acc:
            return cat, rate, reason
    return "S", 19, None


def party_xml(tag: str, p, with_vat: bool) -> str:
    name, street, city, zone, cc = p[0], p[1], p[2], p[3], p[4]
    vatid = p[5]
    endpoint = (f'<cbc:EndpointID schemeID="{p[6]}">{p[7]}</cbc:EndpointID>'
                if len(p) > 6 else f'<cbc:EndpointID schemeID="EM">info@example.test</cbc:EndpointID>')
    vat = (f"""<cac:PartyTaxScheme><cbc:CompanyID>{vatid}</cbc:CompanyID>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>""" if with_vat else "")
    return f"""  <cac:{tag}><cac:Party>
      {endpoint}
      <cac:PartyName><cbc:Name>{name}</cbc:Name></cac:PartyName>
      <cac:PostalAddress><cbc:StreetName>{street}</cbc:StreetName><cbc:CityName>{city}</cbc:CityName>
        <cbc:PostalZone>{zone}</cbc:PostalZone><cac:Country><cbc:IdentificationCode>{cc}</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
      {vat}
      <cac:PartyLegalEntity><cbc:RegistrationName>{name}</cbc:RegistrationName></cac:PartyLegalEntity>
    </cac:Party></cac:{tag}>"""


def invoice(idx: int, seed: int) -> str:
    rng = random.Random(seed * 1_000_003 + idx)
    n = pick_lines(rng)
    cat, rate, reason = pick_scenario(rng)
    seller = SELLERS[rng.randrange(len(SELLERS))]
    buyer = BUYERS[rng.randrange(len(BUYERS))]
    lines, taxable = [], Decimal("0")
    for i in range(1, n + 1):
        item = ITEMS[rng.randrange(len(ITEMS))]
        qty = rng.randint(1, 40)
        net = (item[2] * qty).quantize(C2)
        taxable += net
        lines.append((i, item, qty, net))
    vat = (taxable * rate / 100).quantize(C2, ROUND_HALF_UP) if rate else Decimal("0.00")
    gross = taxable + vat

    def line_xml(i, item, qty, net):
        return f"""  <cac:InvoiceLine><cbc:ID>{i}</cbc:ID>
    <cbc:InvoicedQuantity unitCode="{item[3]}">{qty}</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">{net}</cbc:LineExtensionAmount>
    <cac:Item><cbc:Description>{item[1]}</cbc:Description><cbc:Name>{item[0]}</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>{cat}</cbc:ID><cbc:Percent>{rate}</cbc:Percent>
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory></cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">{item[2]}</cbc:PriceAmount></cac:Price></cac:InvoiceLine>"""

    reason_xml = f"<cbc:TaxExemptionReason>{reason}</cbc:TaxExemptionReason>" if reason else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
  <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
  <cbc:ID>KTR-BENCH-{idx:06d}</cbc:ID>
  <cbc:IssueDate>2026-07-01</cbc:IssueDate>
  <cbc:DueDate>2026-07-31</cbc:DueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cbc:BuyerReference>PO-{idx:06d}</cbc:BuyerReference>
{party_xml("AccountingSupplierParty", seller, True)}
{party_xml("AccountingCustomerParty", buyer, cat == "AE")}
  <cac:PaymentMeans><cbc:PaymentMeansCode>30</cbc:PaymentMeansCode>
    <cbc:PaymentID>KTR-BENCH-{idx:06d}</cbc:PaymentID>
    <cac:PayeeFinancialAccount><cbc:ID>DE89370400440532013000</cbc:ID></cac:PayeeFinancialAccount></cac:PaymentMeans>
  <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">{vat}</cbc:TaxAmount>
    <cac:TaxSubtotal><cbc:TaxableAmount currencyID="EUR">{taxable}</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">{vat}</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>{cat}</cbc:ID><cbc:Percent>{rate}</cbc:Percent>{reason_xml}
        <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>
  <cac:LegalMonetaryTotal><cbc:LineExtensionAmount currencyID="EUR">{taxable}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">{taxable}</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">{gross}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">{gross}</cbc:PayableAmount></cac:LegalMonetaryTotal>
{chr(10).join(line_xml(*ln) for ln in lines)}
</Invoice>"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    corpus = hashlib.sha256()
    mix = {"small": 0, "medium": 0, "large": 0}
    for idx in range(args.count):
        xml = invoice(idx, args.seed).encode("utf-8")
        (args.out / f"bench-{idx:06d}.xml").write_bytes(xml)
        corpus.update(xml)
        # recompute bucket for the printed mix (same rng draw order as invoice())
        rng = random.Random(args.seed * 1_000_003 + idx)
        n = pick_lines(rng)
        mix["small" if n <= 5 else "medium" if n <= 40 else "large"] += 1

    print(f"[bench-corpus] {args.count} invoices (seed {args.seed}) -> {args.out}")
    print(f"[bench-corpus] mix: {mix}")
    print(f"[bench-corpus] sha256: {corpus.hexdigest()}")


if __name__ == "__main__":
    main()

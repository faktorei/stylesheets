<?xml version="1.0" encoding="UTF-8"?>
<!--
  faktorei · normalize/ubl-creditnote.xsl
  UBL 2.1 CreditNote -> faktorei semantic model.

  Imports the invoice normalizer: party, payment, tax and totals templates
  match cac:* elements whose namespaces are identical across both document
  types, so only the root shape and the line element differ. Type code
  defaults to 381; the renderer switches the document title on it.

  License: Apache-2.0
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:si="urn:faktorei:semantic:invoice:1"
    xmlns:cn="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    exclude-result-prefixes="#all">

  <xsl:import href="ubl-invoice.xsl"/>

  <xsl:template match="/cn:CreditNote">
    <si:invoice>
      <si:meta syntax="ubl"
               type-code="{(cbc:CreditNoteTypeCode, '381')[1]}"
               customization="{cbc:CustomizationID}"
               profile="{cbc:ProfileID}"/>

      <si:number bt="BT-1"><xsl:value-of select="cbc:ID"/></si:number>
      <si:issue-date bt="BT-2"><xsl:value-of select="cbc:IssueDate"/></si:issue-date>
      <si:currency bt="BT-5"><xsl:value-of select="cbc:DocumentCurrencyCode"/></si:currency>
      <xsl:if test="cbc:BuyerReference">
        <si:buyer-reference bt="BT-10"><xsl:value-of select="cbc:BuyerReference"/></si:buyer-reference>
      </xsl:if>
      <!-- Preceding invoice reference (BG-3): why this credit note exists -->
      <xsl:for-each select="cac:BillingReference/cac:InvoiceDocumentReference">
        <si:preceding-invoice bt="BT-25" issue-date="{cbc:IssueDate}">
          <xsl:value-of select="cbc:ID"/>
        </si:preceding-invoice>
      </xsl:for-each>
      <xsl:for-each select="cbc:Note">
        <si:note bt="BT-22"><xsl:value-of select="."/></si:note>
      </xsl:for-each>

      <si:seller>
        <xsl:apply-templates select="cac:AccountingSupplierParty/cac:Party" mode="party"/>
      </si:seller>
      <si:buyer>
        <xsl:apply-templates select="cac:AccountingCustomerParty/cac:Party" mode="party"/>
      </si:buyer>

      <xsl:apply-templates select="cac:PaymentMeans[1]"/>
      <xsl:if test="cac:PaymentTerms/cbc:Note">
        <si:payment-terms bt="BT-20"><xsl:value-of select="cac:PaymentTerms/cbc:Note[1]"/></si:payment-terms>
      </xsl:if>

      <si:lines>
        <xsl:apply-templates select="cac:CreditNoteLine"/>
      </si:lines>

      <si:vat-breakdown>
        <xsl:for-each select="cac:TaxTotal/cac:TaxSubtotal">
          <si:group cat="{cac:TaxCategory/cbc:ID}"
                    rate="{(cac:TaxCategory/cbc:Percent, '0')[1]}">
            <si:taxable bt="BT-116"><xsl:value-of select="cbc:TaxableAmount"/></si:taxable>
            <si:tax bt="BT-117"><xsl:value-of select="cbc:TaxAmount"/></si:tax>
            <xsl:if test="cac:TaxCategory/cbc:TaxExemptionReason">
              <si:exemption-reason bt="BT-120">
                <xsl:value-of select="cac:TaxCategory/cbc:TaxExemptionReason"/>
              </si:exemption-reason>
            </xsl:if>
          </si:group>
        </xsl:for-each>
      </si:vat-breakdown>

      <xsl:apply-templates select="cac:LegalMonetaryTotal"/>
    </si:invoice>
  </xsl:template>

  <xsl:template match="cac:CreditNoteLine">
    <si:line>
      <si:id bt="BT-126"><xsl:value-of select="cbc:ID"/></si:id>
      <si:name bt="BT-153"><xsl:value-of select="cac:Item/cbc:Name"/></si:name>
      <xsl:if test="cac:Item/cbc:Description">
        <si:description bt="BT-154"><xsl:value-of select="cac:Item/cbc:Description"/></si:description>
      </xsl:if>
      <si:qty bt="BT-129" unit="{cbc:CreditedQuantity/@unitCode}">
        <xsl:value-of select="cbc:CreditedQuantity"/>
      </si:qty>
      <si:price bt="BT-146"><xsl:value-of select="cac:Price/cbc:PriceAmount"/></si:price>
      <si:net bt="BT-131"><xsl:value-of select="cbc:LineExtensionAmount"/></si:net>
      <si:vat cat="{cac:Item/cac:ClassifiedTaxCategory/cbc:ID}"
              rate="{(cac:Item/cac:ClassifiedTaxCategory/cbc:Percent, '0')[1]}"/>
    </si:line>
  </xsl:template>

</xsl:stylesheet>

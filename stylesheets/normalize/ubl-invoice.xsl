<?xml version="1.0" encoding="UTF-8"?>
<!--
  faktorei · normalize/ubl-invoice.xsl
  Phase 1 of 2: UBL 2.1 Invoice -> faktorei semantic model (urn:faktorei:semantic:invoice:1)

  The semantic model mirrors EN 16931 business terms (BT-/BG-). Each emitted
  element carries a bt="" attribute naming the business term it represents, so
  the renderer and any debugging tooling can trace fields back to the standard.

  Scope of this starter: the fields required to render a correct, complete
  Peppol BIS Billing 3.0 invoice. See stylesheets/semantic/model.md for the
  vocabulary contract and the roadmap of not-yet-mapped terms.

  License: Apache-2.0
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:si="urn:faktorei:semantic:invoice:1"
    xmlns:ubl="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    exclude-result-prefixes="#all">

  <xsl:output method="xml" indent="yes"/>
  <xsl:mode on-no-match="deep-skip"/>

  <xsl:template match="/ubl:Invoice">
    <si:invoice>
      <si:meta syntax="ubl"
               type-code="{(cbc:InvoiceTypeCode, '380')[1]}"
               customization="{cbc:CustomizationID}"
               profile="{cbc:ProfileID}"/>

      <si:number bt="BT-1"><xsl:value-of select="cbc:ID"/></si:number>
      <si:issue-date bt="BT-2"><xsl:value-of select="cbc:IssueDate"/></si:issue-date>
      <xsl:if test="cbc:DueDate">
        <si:due-date bt="BT-9"><xsl:value-of select="cbc:DueDate"/></si:due-date>
      </xsl:if>
      <si:currency bt="BT-5"><xsl:value-of select="cbc:DocumentCurrencyCode"/></si:currency>
      <xsl:if test="cbc:BuyerReference">
        <si:buyer-reference bt="BT-10"><xsl:value-of select="cbc:BuyerReference"/></si:buyer-reference>
      </xsl:if>
      <xsl:if test="cac:OrderReference/cbc:ID">
        <si:order-reference bt="BT-13"><xsl:value-of select="cac:OrderReference/cbc:ID"/></si:order-reference>
      </xsl:if>
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

      <xsl:if test="cac:AllowanceCharge">
        <si:allowances-charges>
          <xsl:for-each select="cac:AllowanceCharge">
            <si:item kind="{if (cbc:ChargeIndicator = 'true') then 'charge' else 'allowance'}"
                     reason="{(cbc:AllowanceChargeReason, cbc:AllowanceChargeReasonCode)[1]}">
              <si:amount><xsl:value-of select="cbc:Amount"/></si:amount>
              <si:vat cat="{cac:TaxCategory/cbc:ID}"
                      rate="{(cac:TaxCategory/cbc:Percent, '0')[1]}"/>
            </si:item>
          </xsl:for-each>
        </si:allowances-charges>
      </xsl:if>

      <si:lines>
        <xsl:apply-templates select="cac:InvoiceLine"/>
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

  <!-- ============ Party (BG-4 seller / BG-7 buyer share a shape) ============ -->
  <xsl:template match="cac:Party" mode="party">
    <si:name>
      <xsl:value-of select="(cac:PartyLegalEntity/cbc:RegistrationName,
                             cac:PartyName/cbc:Name)[1]"/>
    </si:name>
    <xsl:if test="cbc:EndpointID">
      <si:endpoint scheme="{cbc:EndpointID/@schemeID}">
        <xsl:value-of select="cbc:EndpointID"/>
      </si:endpoint>
    </xsl:if>
    <xsl:if test="cac:PartyTaxScheme[cac:TaxScheme/cbc:ID = 'VAT']/cbc:CompanyID">
      <si:vat-id>
        <xsl:value-of select="cac:PartyTaxScheme[cac:TaxScheme/cbc:ID = 'VAT']/cbc:CompanyID"/>
      </si:vat-id>
    </xsl:if>
    <xsl:if test="cac:PartyLegalEntity/cbc:CompanyID">
      <si:legal-id scheme="{cac:PartyLegalEntity/cbc:CompanyID/@schemeID}">
        <xsl:value-of select="cac:PartyLegalEntity/cbc:CompanyID"/>
      </si:legal-id>
    </xsl:if>
    <xsl:for-each select="cac:PostalAddress">
      <si:address>
        <xsl:for-each select="cbc:StreetName, cac:AddressLine/cbc:Line">
          <si:line><xsl:value-of select="."/></si:line>
        </xsl:for-each>
        <si:city><xsl:value-of select="cbc:CityName"/></si:city>
        <si:postcode><xsl:value-of select="cbc:PostalZone"/></si:postcode>
        <si:country><xsl:value-of select="cac:Country/cbc:IdentificationCode"/></si:country>
      </si:address>
    </xsl:for-each>
    <xsl:if test="cac:Contact/(cbc:Name | cbc:ElectronicMail | cbc:Telephone)">
      <si:contact>
        <xsl:if test="cac:Contact/cbc:Name"><si:person><xsl:value-of select="cac:Contact/cbc:Name"/></si:person></xsl:if>
        <xsl:if test="cac:Contact/cbc:ElectronicMail"><si:email><xsl:value-of select="cac:Contact/cbc:ElectronicMail"/></si:email></xsl:if>
        <xsl:if test="cac:Contact/cbc:Telephone"><si:phone><xsl:value-of select="cac:Contact/cbc:Telephone"/></si:phone></xsl:if>
      </si:contact>
    </xsl:if>
  </xsl:template>

  <!-- ============ Payment means (BG-16) ============ -->
  <xsl:template match="cac:PaymentMeans">
    <si:payment>
      <si:means-code bt="BT-81"><xsl:value-of select="cbc:PaymentMeansCode"/></si:means-code>
      <xsl:if test="cbc:PaymentID">
        <si:remittance bt="BT-83"><xsl:value-of select="cbc:PaymentID"/></si:remittance>
      </xsl:if>
      <xsl:if test="cac:PayeeFinancialAccount/cbc:ID">
        <si:iban bt="BT-84"><xsl:value-of select="cac:PayeeFinancialAccount/cbc:ID"/></si:iban>
      </xsl:if>
      <xsl:if test="cac:PayeeFinancialAccount/cbc:Name">
        <si:account-name bt="BT-85"><xsl:value-of select="cac:PayeeFinancialAccount/cbc:Name"/></si:account-name>
      </xsl:if>
    </si:payment>
  </xsl:template>

  <!-- ============ Invoice line (BG-25) ============ -->
  <xsl:template match="cac:InvoiceLine">
    <si:line>
      <si:id bt="BT-126"><xsl:value-of select="cbc:ID"/></si:id>
      <si:name bt="BT-153"><xsl:value-of select="cac:Item/cbc:Name"/></si:name>
      <xsl:if test="cac:Item/cbc:Description">
        <si:description bt="BT-154"><xsl:value-of select="cac:Item/cbc:Description"/></si:description>
      </xsl:if>
      <si:qty bt="BT-129" unit="{cbc:InvoicedQuantity/@unitCode}">
        <xsl:value-of select="cbc:InvoicedQuantity"/>
      </si:qty>
      <si:price bt="BT-146"><xsl:value-of select="cac:Price/cbc:PriceAmount"/></si:price>
      <si:net bt="BT-131"><xsl:value-of select="cbc:LineExtensionAmount"/></si:net>
      <si:vat cat="{cac:Item/cac:ClassifiedTaxCategory/cbc:ID}"
              rate="{(cac:Item/cac:ClassifiedTaxCategory/cbc:Percent, '0')[1]}"/>
    </si:line>
  </xsl:template>

  <!-- ============ Document totals (BG-22) ============ -->
  <xsl:template match="cac:LegalMonetaryTotal">
    <si:totals>
      <si:line-net bt="BT-106"><xsl:value-of select="cbc:LineExtensionAmount"/></si:line-net>
      <xsl:if test="cbc:AllowanceTotalAmount">
        <si:allowances bt="BT-107"><xsl:value-of select="cbc:AllowanceTotalAmount"/></si:allowances>
      </xsl:if>
      <xsl:if test="cbc:ChargeTotalAmount">
        <si:charges bt="BT-108"><xsl:value-of select="cbc:ChargeTotalAmount"/></si:charges>
      </xsl:if>
      <si:net bt="BT-109"><xsl:value-of select="cbc:TaxExclusiveAmount"/></si:net>
      <si:vat bt="BT-110"><xsl:value-of select="../cac:TaxTotal[1]/cbc:TaxAmount"/></si:vat>
      <si:gross bt="BT-112"><xsl:value-of select="cbc:TaxInclusiveAmount"/></si:gross>
      <xsl:if test="cbc:PrepaidAmount">
        <si:prepaid bt="BT-113"><xsl:value-of select="cbc:PrepaidAmount"/></si:prepaid>
      </xsl:if>
      <xsl:if test="cbc:PayableRoundingAmount">
        <si:rounding bt="BT-114"><xsl:value-of select="cbc:PayableRoundingAmount"/></si:rounding>
      </xsl:if>
      <si:due bt="BT-115"><xsl:value-of select="cbc:PayableAmount"/></si:due>
    </si:totals>
  </xsl:template>

</xsl:stylesheet>

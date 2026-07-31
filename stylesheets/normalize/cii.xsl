<?xml version="1.0" encoding="UTF-8"?>
<!--
  faktorei · normalize/cii.xsl
  UN/CEFACT Cross Industry Invoice (D16B, EN 16931 subset) -> faktorei semantic model.

  Implementation guide: the EN 16931-3-3 CII syntax mapping tables. The
  equivalence contract (enforced by tools/test_equivalence.py): a CII document
  and a UBL document carrying the same business content MUST normalize to
  identical semantic XML apart from <si:meta> attributes.

  CII notes vs UBL:
    * Dates arrive as udt:DateTimeString @format="102" (CCYYMMDD) — converted
      to ISO here so the renderer never sees syntax-specific formats.
    * BT-9 (due date) and BT-20 (payment terms) both live under
      SpecifiedTradePaymentTerms.
    * The document type code plays the invoice/credit-note role (380/381);
      CII has no separate credit-note document shape.

  License: Apache-2.0
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:si="urn:faktorei:semantic:invoice:1"
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100"
    xmlns:kf="urn:faktorei:fn:normalize"
    exclude-result-prefixes="#all">

  <xsl:output method="xml" indent="yes"/>
  <xsl:mode on-no-match="deep-skip"/>

  <!-- CCYYMMDD (format 102) -> ISO date -->
  <xsl:function name="kf:d" as="xs:string">
    <xsl:param name="v" as="xs:string?"/>
    <xsl:sequence select="if (string-length($v) = 8)
        then concat(substring($v,1,4), '-', substring($v,5,2), '-', substring($v,7,2))
        else string($v)"/>
  </xsl:function>

  <xsl:template match="/rsm:CrossIndustryInvoice">
    <xsl:variable name="doc" select="rsm:ExchangedDocument"/>
    <xsl:variable name="tx" select="rsm:SupplyChainTradeTransaction"/>
    <xsl:variable name="agr" select="$tx/ram:ApplicableHeaderTradeAgreement"/>
    <xsl:variable name="stl" select="$tx/ram:ApplicableHeaderTradeSettlement"/>

    <si:invoice>
      <si:meta syntax="cii"
               type-code="{($doc/ram:TypeCode, '380')[1]}"
               customization="{rsm:ExchangedDocumentContext/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID}"
               profile="{rsm:ExchangedDocumentContext/ram:BusinessProcessSpecifiedDocumentContextParameter/ram:ID}"/>

      <si:number bt="BT-1"><xsl:value-of select="$doc/ram:ID"/></si:number>
      <si:issue-date bt="BT-2">
        <xsl:value-of select="kf:d($doc/ram:IssueDateTime/udt:DateTimeString)"/>
      </si:issue-date>
      <xsl:if test="$stl/ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime">
        <si:due-date bt="BT-9">
          <xsl:value-of select="kf:d($stl/ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString)"/>
        </si:due-date>
      </xsl:if>
      <si:currency bt="BT-5"><xsl:value-of select="$stl/ram:InvoiceCurrencyCode"/></si:currency>
      <xsl:if test="$agr/ram:BuyerReference">
        <si:buyer-reference bt="BT-10"><xsl:value-of select="$agr/ram:BuyerReference"/></si:buyer-reference>
      </xsl:if>
      <xsl:if test="$agr/ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID">
        <si:order-reference bt="BT-13">
          <xsl:value-of select="$agr/ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID"/>
        </si:order-reference>
      </xsl:if>
      <xsl:for-each select="$doc/ram:IncludedNote">
        <si:note bt="BT-22"><xsl:value-of select="ram:Content"/></si:note>
      </xsl:for-each>

      <si:seller>
        <xsl:apply-templates select="$agr/ram:SellerTradeParty" mode="cii-party"/>
      </si:seller>
      <si:buyer>
        <xsl:apply-templates select="$agr/ram:BuyerTradeParty" mode="cii-party"/>
      </si:buyer>

      <xsl:for-each select="$stl/ram:SpecifiedTradeSettlementPaymentMeans[1]">
        <si:payment>
          <si:means-code bt="BT-81"><xsl:value-of select="ram:TypeCode"/></si:means-code>
          <xsl:if test="$stl/ram:PaymentReference">
            <si:remittance bt="BT-83"><xsl:value-of select="$stl/ram:PaymentReference"/></si:remittance>
          </xsl:if>
          <xsl:if test="ram:PayeePartyCreditorFinancialAccount/ram:IBANID">
            <si:iban bt="BT-84"><xsl:value-of select="ram:PayeePartyCreditorFinancialAccount/ram:IBANID"/></si:iban>
          </xsl:if>
          <xsl:if test="ram:PayeePartyCreditorFinancialAccount/ram:AccountName">
            <si:account-name bt="BT-85">
              <xsl:value-of select="ram:PayeePartyCreditorFinancialAccount/ram:AccountName"/>
            </si:account-name>
          </xsl:if>
        </si:payment>
      </xsl:for-each>
      <xsl:if test="$stl/ram:SpecifiedTradePaymentTerms/ram:Description">
        <si:payment-terms bt="BT-20">
          <xsl:value-of select="$stl/ram:SpecifiedTradePaymentTerms/ram:Description[1]"/>
        </si:payment-terms>
      </xsl:if>

      <xsl:if test="$stl/ram:SpecifiedTradeAllowanceCharge">
        <si:allowances-charges>
          <xsl:for-each select="$stl/ram:SpecifiedTradeAllowanceCharge">
            <si:item kind="{if (ram:ChargeIndicator/udt:Indicator = 'true') then 'charge' else 'allowance'}"
                     reason="{(ram:Reason, ram:ReasonCode)[1]}">
              <si:amount><xsl:value-of select="ram:ActualAmount"/></si:amount>
              <si:vat cat="{ram:CategoryTradeTax/ram:CategoryCode}"
                      rate="{(ram:CategoryTradeTax/ram:RateApplicablePercent, '0')[1]}"/>
            </si:item>
          </xsl:for-each>
        </si:allowances-charges>
      </xsl:if>

      <si:lines>
        <xsl:apply-templates select="$tx/ram:IncludedSupplyChainTradeLineItem"/>
      </si:lines>

      <si:vat-breakdown>
        <xsl:for-each select="$stl/ram:ApplicableTradeTax">
          <si:group cat="{ram:CategoryCode}"
                    rate="{(ram:RateApplicablePercent, '0')[1]}">
            <si:taxable bt="BT-116"><xsl:value-of select="ram:BasisAmount"/></si:taxable>
            <si:tax bt="BT-117"><xsl:value-of select="ram:CalculatedAmount"/></si:tax>
            <xsl:if test="ram:ExemptionReason">
              <si:exemption-reason bt="BT-120"><xsl:value-of select="ram:ExemptionReason"/></si:exemption-reason>
            </xsl:if>
          </si:group>
        </xsl:for-each>
      </si:vat-breakdown>

      <xsl:for-each select="$stl/ram:SpecifiedTradeSettlementHeaderMonetarySummation">
        <si:totals>
          <si:line-net bt="BT-106"><xsl:value-of select="ram:LineTotalAmount"/></si:line-net>
          <xsl:if test="ram:AllowanceTotalAmount">
            <si:allowances bt="BT-107"><xsl:value-of select="ram:AllowanceTotalAmount"/></si:allowances>
          </xsl:if>
          <xsl:if test="ram:ChargeTotalAmount">
            <si:charges bt="BT-108"><xsl:value-of select="ram:ChargeTotalAmount"/></si:charges>
          </xsl:if>
          <si:net bt="BT-109"><xsl:value-of select="ram:TaxBasisTotalAmount"/></si:net>
          <si:vat bt="BT-110"><xsl:value-of select="ram:TaxTotalAmount"/></si:vat>
          <si:gross bt="BT-112"><xsl:value-of select="ram:GrandTotalAmount"/></si:gross>
          <xsl:if test="ram:TotalPrepaidAmount">
            <si:prepaid bt="BT-113"><xsl:value-of select="ram:TotalPrepaidAmount"/></si:prepaid>
          </xsl:if>
          <xsl:if test="ram:RoundingAmount">
            <si:rounding bt="BT-114"><xsl:value-of select="ram:RoundingAmount"/></si:rounding>
          </xsl:if>
          <si:due bt="BT-115"><xsl:value-of select="ram:DuePayableAmount"/></si:due>
        </si:totals>
      </xsl:for-each>
    </si:invoice>
  </xsl:template>

  <!-- ============ Trade party (BG-4 / BG-7) ============ -->
  <xsl:template match="ram:SellerTradeParty | ram:BuyerTradeParty" mode="cii-party">
    <si:name><xsl:value-of select="ram:Name"/></si:name>
    <xsl:if test="ram:URIUniversalCommunication/ram:URIID">
      <si:endpoint scheme="{ram:URIUniversalCommunication/ram:URIID/@schemeID}">
        <xsl:value-of select="ram:URIUniversalCommunication/ram:URIID"/>
      </si:endpoint>
    </xsl:if>
    <xsl:if test="ram:SpecifiedTaxRegistration/ram:ID[@schemeID = 'VA']">
      <si:vat-id><xsl:value-of select="ram:SpecifiedTaxRegistration/ram:ID[@schemeID = 'VA']"/></si:vat-id>
    </xsl:if>
    <xsl:if test="ram:SpecifiedLegalOrganization/ram:ID">
      <si:legal-id scheme="{ram:SpecifiedLegalOrganization/ram:ID/@schemeID}">
        <xsl:value-of select="ram:SpecifiedLegalOrganization/ram:ID"/>
      </si:legal-id>
    </xsl:if>
    <xsl:for-each select="ram:PostalTradeAddress">
      <si:address>
        <xsl:for-each select="ram:LineOne, ram:LineTwo, ram:LineThree">
          <si:line><xsl:value-of select="."/></si:line>
        </xsl:for-each>
        <si:city><xsl:value-of select="ram:CityName"/></si:city>
        <si:postcode><xsl:value-of select="ram:PostcodeCode"/></si:postcode>
        <si:country><xsl:value-of select="ram:CountryID"/></si:country>
      </si:address>
    </xsl:for-each>
    <xsl:if test="ram:DefinedTradeContact/(ram:PersonName | ram:EmailURIUniversalCommunication | ram:TelephoneUniversalCommunication)">
      <si:contact>
        <xsl:if test="ram:DefinedTradeContact/ram:PersonName">
          <si:person><xsl:value-of select="ram:DefinedTradeContact/ram:PersonName"/></si:person>
        </xsl:if>
        <xsl:if test="ram:DefinedTradeContact/ram:EmailURIUniversalCommunication/ram:URIID">
          <si:email><xsl:value-of select="ram:DefinedTradeContact/ram:EmailURIUniversalCommunication/ram:URIID"/></si:email>
        </xsl:if>
        <xsl:if test="ram:DefinedTradeContact/ram:TelephoneUniversalCommunication/ram:CompleteNumber">
          <si:phone><xsl:value-of select="ram:DefinedTradeContact/ram:TelephoneUniversalCommunication/ram:CompleteNumber"/></si:phone>
        </xsl:if>
      </si:contact>
    </xsl:if>
  </xsl:template>

  <!-- ============ Line item (BG-25) ============ -->
  <xsl:template match="ram:IncludedSupplyChainTradeLineItem">
    <si:line>
      <si:id bt="BT-126"><xsl:value-of select="ram:AssociatedDocumentLineDocument/ram:LineID"/></si:id>
      <si:name bt="BT-153"><xsl:value-of select="ram:SpecifiedTradeProduct/ram:Name"/></si:name>
      <xsl:if test="ram:SpecifiedTradeProduct/ram:Description">
        <si:description bt="BT-154"><xsl:value-of select="ram:SpecifiedTradeProduct/ram:Description"/></si:description>
      </xsl:if>
      <si:qty bt="BT-129" unit="{ram:SpecifiedLineTradeDelivery/ram:BilledQuantity/@unitCode}">
        <xsl:value-of select="ram:SpecifiedLineTradeDelivery/ram:BilledQuantity"/>
      </si:qty>
      <si:price bt="BT-146">
        <xsl:value-of select="ram:SpecifiedLineTradeAgreement/ram:NetPriceProductTradePrice/ram:ChargeAmount"/>
      </si:price>
      <si:net bt="BT-131">
        <xsl:value-of select="ram:SpecifiedLineTradeSettlement/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount"/>
      </si:net>
      <si:vat cat="{ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:CategoryCode}"
              rate="{(ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent, '0')[1]}"/>
    </si:line>
  </xsl:template>

</xsl:stylesheet>

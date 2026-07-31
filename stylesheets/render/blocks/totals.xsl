<?xml version="1.0" encoding="UTF-8"?>
<!--
  faktorei · blocks/totals.xsl — VAT breakdown, document totals (BG-22),
  payment instructions. keep-together discipline comes from the theme's
  totals.block set: the totals must never orphan across a page break.
  License: Apache-2.0
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    xmlns:si="urn:faktorei:semantic:invoice:1"
    xmlns:k="urn:faktorei:fn"
    exclude-result-prefixes="#all">

  <xsl:template name="totals-block">
    <xsl:variable name="currency" select="si:currency"/>
    <fo:block xsl:use-attribute-sets="totals.block">
      <fo:table table-layout="fixed" width="100%">
        <fo:table-column column-width="52%"/>
        <fo:table-column column-width="48%"/>
        <fo:table-body>
          <fo:table-row>
            <!-- Left: VAT breakdown + payment -->
            <fo:table-cell padding-right="8mm">
              <xsl:call-template name="vat-breakdown"/>
              <xsl:apply-templates select="si:payment"/>
              <xsl:if test="si:payment-terms">
                <fo:block space-before="2mm" font-size="8pt" color="#5A5F68">
                  <xsl:value-of select="si:payment-terms"/>
                </fo:block>
              </xsl:if>
            </fo:table-cell>
            <!-- Right: document totals -->
            <fo:table-cell>
              <xsl:call-template name="doc-totals"/>
            </fo:table-cell>
          </fo:table-row>
        </fo:table-body>
      </fo:table>
    </fo:block>
    <fo:block id="faktorei-doc-end"/>
  </xsl:template>

  <xsl:template name="vat-breakdown">
    <fo:block xsl:use-attribute-sets="label">
      <xsl:value-of select="k:t('vat.breakdown')"/>
    </fo:block>
    <fo:table table-layout="fixed" width="100%" space-before="1mm">
      <fo:table-column column-width="30%"/>
      <fo:table-column column-width="35%"/>
      <fo:table-column column-width="35%"/>
      <fo:table-body>
        <xsl:for-each select="si:vat-breakdown/si:group">
          <fo:table-row>
            <fo:table-cell xsl:use-attribute-sets="totals.cell">
              <fo:block><xsl:value-of select="@cat"/><xsl:text> · </xsl:text><xsl:value-of select="@rate"/>%</fo:block>
            </fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="totals.cellNum">
              <fo:block><xsl:value-of select="k:money(si:taxable)"/></fo:block>
            </fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="totals.cellNum">
              <fo:block><xsl:value-of select="k:money(si:tax)"/></fo:block>
            </fo:table-cell>
          </fo:table-row>
          <xsl:if test="si:exemption-reason">
            <fo:table-row>
              <fo:table-cell number-columns-spanned="3" xsl:use-attribute-sets="totals.cell">
                <fo:block font-size="7.5pt" color="#5A5F68">
                  <xsl:value-of select="si:exemption-reason"/>
                </fo:block>
              </fo:table-cell>
            </fo:table-row>
          </xsl:if>
        </xsl:for-each>
      </fo:table-body>
    </fo:table>
  </xsl:template>

  <xsl:template name="doc-totals">
    <xsl:variable name="currency" select="si:currency"/>
    <fo:table table-layout="fixed" width="100%">
      <fo:table-column column-width="55%"/>
      <fo:table-column column-width="45%"/>
      <fo:table-body>
        <xsl:call-template name="total-row">
          <xsl:with-param name="label" select="k:t('totals.net')"/>
          <xsl:with-param name="value" select="si:totals/si:net"/>
        </xsl:call-template>
        <xsl:if test="si:totals/si:allowances">
          <xsl:call-template name="total-row">
            <xsl:with-param name="label" select="k:t('totals.allowances')"/>
            <xsl:with-param name="value" select="concat('-', si:totals/si:allowances)"/>
          </xsl:call-template>
        </xsl:if>
        <xsl:if test="si:totals/si:charges">
          <xsl:call-template name="total-row">
            <xsl:with-param name="label" select="k:t('totals.charges')"/>
            <xsl:with-param name="value" select="si:totals/si:charges"/>
          </xsl:call-template>
        </xsl:if>
        <xsl:call-template name="total-row">
          <xsl:with-param name="label" select="k:t('totals.vat')"/>
          <xsl:with-param name="value" select="si:totals/si:vat"/>
        </xsl:call-template>
        <xsl:if test="si:totals/si:prepaid">
          <xsl:call-template name="total-row">
            <xsl:with-param name="label" select="k:t('totals.prepaid')"/>
            <xsl:with-param name="value" select="concat('-', si:totals/si:prepaid)"/>
          </xsl:call-template>
        </xsl:if>
        <xsl:if test="si:totals/si:rounding">
          <xsl:call-template name="total-row">
            <xsl:with-param name="label" select="k:t('totals.rounding')"/>
            <xsl:with-param name="value" select="si:totals/si:rounding"/>
          </xsl:call-template>
        </xsl:if>
        <fo:table-row xsl:use-attribute-sets="totals.dueRow">
          <fo:table-cell xsl:use-attribute-sets="totals.cell">
            <fo:block font-weight="bold">
              <xsl:value-of select="k:t('totals.due')"/>
              <xsl:text> </xsl:text><xsl:value-of select="$currency"/>
            </fo:block>
          </fo:table-cell>
          <fo:table-cell xsl:use-attribute-sets="totals.cellNum">
            <fo:block font-weight="bold" font-size="10.5pt">
              <xsl:value-of select="k:money(si:totals/si:due)"/>
            </fo:block>
          </fo:table-cell>
        </fo:table-row>
      </fo:table-body>
    </fo:table>
  </xsl:template>

  <xsl:template name="total-row">
    <xsl:param name="label"/>
    <xsl:param name="value"/>
    <fo:table-row>
      <fo:table-cell xsl:use-attribute-sets="totals.cell">
        <fo:block><xsl:value-of select="$label"/></fo:block>
      </fo:table-cell>
      <fo:table-cell xsl:use-attribute-sets="totals.cellNum">
        <fo:block><xsl:value-of select="k:money($value)"/></fo:block>
      </fo:table-cell>
    </fo:table-row>
  </xsl:template>

  <xsl:template match="si:payment">
    <fo:block space-before="4mm">
      <fo:block xsl:use-attribute-sets="label">
        <xsl:value-of select="k:t('payment.title')"/>
      </fo:block>
      <xsl:if test="si:iban">
        <fo:block space-before="1mm">
          <xsl:value-of select="k:t('payment.iban')"/><xsl:text> </xsl:text>
          <fo:inline xsl:use-attribute-sets="meta.value accent">
            <xsl:value-of select="si:iban"/>
          </fo:inline>
        </fo:block>
      </xsl:if>
      <xsl:if test="si:remittance">
        <fo:block font-size="8pt">
          <xsl:value-of select="k:t('payment.reference')"/><xsl:text> </xsl:text>
          <fo:inline xsl:use-attribute-sets="meta.value" font-size="8pt">
            <xsl:value-of select="si:remittance"/>
          </fo:inline>
        </fo:block>
      </xsl:if>
    </fo:block>
  </xsl:template>

</xsl:stylesheet>

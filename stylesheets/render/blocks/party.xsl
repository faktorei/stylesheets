<?xml version="1.0" encoding="UTF-8"?>
<!-- faktorei · blocks/party.xsl — billed-to / supplier panels. License: Apache-2.0 -->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    xmlns:si="urn:faktorei:semantic:invoice:1"
    xmlns:k="urn:faktorei:fn"
    exclude-result-prefixes="#all">

  <xsl:template name="party-block">
    <fo:table table-layout="fixed" width="100%">
      <fo:table-column column-width="50%"/>
      <fo:table-column column-width="50%"/>
      <fo:table-body>
        <fo:table-row>
          <fo:table-cell padding-right="6mm">
            <fo:block xsl:use-attribute-sets="label">
              <xsl:value-of select="k:t('party.billto')"/>
            </fo:block>
            <xsl:apply-templates select="si:buyer" mode="party-panel"/>
          </fo:table-cell>
          <fo:table-cell>
            <fo:block xsl:use-attribute-sets="label">
              <xsl:value-of select="k:t('party.supplier')"/>
            </fo:block>
            <xsl:apply-templates select="si:seller" mode="party-panel"/>
          </fo:table-cell>
        </fo:table-row>
      </fo:table-body>
    </fo:table>
  </xsl:template>

  <xsl:template match="si:buyer | si:seller" mode="party-panel">
    <fo:block font-weight="bold" space-after="0.6mm"><xsl:value-of select="si:name"/></fo:block>
    <xsl:for-each select="si:address/si:line">
      <fo:block><xsl:value-of select="."/></fo:block>
    </xsl:for-each>
    <fo:block>
      <xsl:value-of select="string-join((si:address/si:postcode, si:address/si:city), ' ')"/>
      <xsl:if test="si:address/si:country">
        <xsl:text> · </xsl:text><xsl:value-of select="si:address/si:country"/>
      </xsl:if>
    </fo:block>
    <xsl:if test="si:vat-id">
      <fo:block space-before="0.8mm" font-size="8pt">
        <xsl:value-of select="k:t('party.vatid')"/><xsl:text> </xsl:text>
        <fo:inline xsl:use-attribute-sets="meta.value" font-size="8pt">
          <xsl:value-of select="si:vat-id"/>
        </fo:inline>
      </fo:block>
    </xsl:if>
    <!-- XRechnung mandates the seller contact triple (BR-DE-5/6/7): show the
         person and phone the profile guarantees; email renders for any party. -->
    <xsl:if test="$profile-resolved = 'xrechnung' and self::si:seller and si:contact/si:person">
      <fo:block space-before="0.8mm" font-size="8pt" color="#5A5F68">
        <xsl:value-of select="si:contact/si:person"/>
      </fo:block>
    </xsl:if>
    <xsl:if test="si:contact/si:email">
      <fo:block font-size="8pt" color="#5A5F68"><xsl:value-of select="si:contact/si:email"/></fo:block>
    </xsl:if>
    <xsl:if test="$profile-resolved = 'xrechnung' and self::si:seller and si:contact/si:phone">
      <fo:block font-size="8pt" color="#5A5F68">
        <xsl:value-of select="k:t('party.phone')"/><xsl:text> </xsl:text>
        <xsl:value-of select="si:contact/si:phone"/>
      </fo:block>
    </xsl:if>
  </xsl:template>

</xsl:stylesheet>

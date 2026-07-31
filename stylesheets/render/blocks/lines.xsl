<?xml version="1.0" encoding="UTF-8"?>
<!--
  faktorei · blocks/lines.xsl — the line-item table.

  Pagination machinery:
    * fo:table-header repeats column headings on every page automatically.
    * Continuation-page subtotals use the classic "Brought forward" pattern:
      each row plants an fo:marker carrying the cumulative net of all
      PRECEDING rows (empty on row 1); a header row retrieves
      first-starting-within-page, so every continuation page opens with the
      amount brought into it. Page 1 retrieves row 1's empty marker and the
      row collapses to nothing.

  FORMATTER NOTE (empirical, FOP 2.8): FOP resolves fo:retrieve-table-marker
  as first-starting-within-page regardless of the requested
  retrieve-position-within-table — "last-ending-within-page" (the footer
  "Carried forward" pattern) silently returns the page's FIRST marker. Hence
  the header-side design here, which is correct under both conformant and
  FOP semantics. Commercial formatters (RenderX, Antenna House) implement
  last-ending correctly; a footer "Carried forward" variant can be offered
  behind the formatter abstraction seam (plan §3, §10). Covered by the
  corpus pagination fixture; re-verify on any FOP upgrade.

  License: Apache-2.0
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    xmlns:si="urn:faktorei:semantic:invoice:1"
    xmlns:k="urn:faktorei:fn"
    exclude-result-prefixes="#all">

  <xsl:template match="si:lines">
    <xsl:variable name="currency" select="/si:invoice/si:currency"/>
    <fo:table xsl:use-attribute-sets="lines.table">
      <fo:table-column column-width="7%"/>
      <fo:table-column column-width="41%"/>
      <fo:table-column column-width="11%"/>
      <fo:table-column column-width="14%"/>
      <fo:table-column column-width="10%"/>
      <fo:table-column column-width="17%"/>

      <fo:table-header>
        <fo:table-row>
          <fo:table-cell xsl:use-attribute-sets="lines.headerCell">
            <fo:block><xsl:value-of select="k:t('lines.pos')"/></fo:block>
          </fo:table-cell>
          <fo:table-cell xsl:use-attribute-sets="lines.headerCell">
            <fo:block><xsl:value-of select="k:t('lines.item')"/></fo:block>
          </fo:table-cell>
          <fo:table-cell xsl:use-attribute-sets="lines.headerCell">
            <fo:block text-align="right"><xsl:value-of select="k:t('lines.qty')"/></fo:block>
          </fo:table-cell>
          <fo:table-cell xsl:use-attribute-sets="lines.headerCell">
            <fo:block text-align="right">
              <xsl:value-of select="k:t('lines.price')"/>
              <xsl:text> </xsl:text><xsl:value-of select="$currency"/>
            </fo:block>
          </fo:table-cell>
          <fo:table-cell xsl:use-attribute-sets="lines.headerCell">
            <fo:block text-align="right"><xsl:value-of select="k:t('lines.vat')"/></fo:block>
          </fo:table-cell>
          <fo:table-cell xsl:use-attribute-sets="lines.headerCell">
            <fo:block text-align="right">
              <xsl:value-of select="k:t('lines.net')"/>
              <xsl:text> </xsl:text><xsl:value-of select="$currency"/>
            </fo:block>
          </fo:table-cell>
        </fo:table-row>
        <!-- Brought-forward row. The carried total is supplied per page by the
             retrieved marker; the leading nbsp is STATIC so FOP reserves one line
             for this header row. FOP fixes the repeated header's height from its
             static layout (before any marker is retrieved) — without the static
             nbsp the cell measures as zero-height and the carried total overflows
             onto the first line of every continuation page. On page 1 the marker
             is empty, so the row shows a single blank line under the headings. -->
        <fo:table-row>
          <fo:table-cell number-columns-spanned="6" xsl:use-attribute-sets="lines.broughtRow">
            <fo:block text-align="right"><xsl:text>&#160;</xsl:text>
              <fo:retrieve-table-marker retrieve-class-name="carry"
                  retrieve-position-within-table="first-starting"
                  retrieve-boundary-within-table="table"/>
            </fo:block>
          </fo:table-cell>
        </fo:table-row>
      </fo:table-header>

      <fo:table-body>
        <xsl:for-each select="si:line">
          <xsl:variable name="before"
              select="sum(preceding-sibling::si:line/xs:decimal(si:net))"/>
          <fo:table-row>
            <xsl:if test="position() mod 2 = 0">
              <xsl:attribute name="background-color">
                <xsl:value-of select="$theme.zebra"/>
              </xsl:attribute>
            </xsl:if>
            <fo:table-cell xsl:use-attribute-sets="lines.cellPos">
              <fo:block>
                <fo:marker marker-class-name="carry">
                  <xsl:if test="position() gt 1">
                    <xsl:value-of select="k:t('lines.broughtfwd')"/>
                    <xsl:text>   </xsl:text>
                    <xsl:value-of select="k:money($before)"/>
                  </xsl:if>
                </fo:marker>
                <xsl:value-of select="si:id"/>
              </fo:block>
            </fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="lines.cell">
              <fo:block><xsl:value-of select="si:name"/></fo:block>
              <xsl:if test="si:description">
                <fo:block font-size="7.5pt" color="#5A5F68"><xsl:value-of select="si:description"/></fo:block>
              </xsl:if>
            </fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="lines.cellNum">
              <fo:block>
                <xsl:value-of select="k:qty(si:qty)"/>
                <fo:inline font-size="7pt" color="#5A5F68">
                  <xsl:text> </xsl:text><xsl:value-of select="si:qty/@unit"/>
                </fo:inline>
              </fo:block>
            </fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="lines.cellNum">
              <fo:block><xsl:value-of select="k:money(si:price)"/></fo:block>
            </fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="lines.cellNum">
              <fo:block><xsl:value-of select="si:vat/@rate"/>%</fo:block>
            </fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="lines.cellNum">
              <fo:block><xsl:value-of select="k:money(si:net)"/></fo:block>
            </fo:table-cell>
          </fo:table-row>
        </xsl:for-each>
      </fo:table-body>
    </fo:table>
  </xsl:template>

</xsl:stylesheet>

<?xml version="1.0" encoding="UTF-8"?>
<!--
  faktorei · render/layout.xsl
  Phase 2 of 2: faktorei semantic model -> XSL-FO.

  Structure lives here and in blocks/*; styling lives exclusively in the
  imported theme (see themes/ledger.xsl for the theming contract).

  Public parameters (full reference: stylesheets/config/params.md):
    lang        label language, matches i18n/labels-{lang}.xml   [en]
    theme.*     see theme file
    logo-uri    optional image URI placed top-left               ['']
    accent      convenience alias for theme.accent
    profile     presentation profile: auto|generic|xrechnung     [auto]
                auto derives from BT-24 (si:meta/@customization)

  License: Apache-2.0
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:fo="http://www.w3.org/1999/XSL/Format"
    xmlns:si="urn:faktorei:semantic:invoice:1"
    xmlns:k="urn:faktorei:fn"
    exclude-result-prefixes="#all">

  <xsl:import href="themes/ledger.xsl"/>
  <xsl:import href="blocks/party.xsl"/>
  <xsl:import href="blocks/lines.xsl"/>
  <xsl:import href="blocks/totals.xsl"/>

  <xsl:output method="xml" indent="no"/>

  <xsl:param name="lang" select="'en'"/>
  <xsl:param name="logo-uri" select="''"/>
  <xsl:param name="profile" select="'auto'"/>  <!-- auto | generic | xrechnung | pint-a-nz -->

  <!-- 'auto' resolves the presentation profile from BT-24: both KoSIT URN
       generations carry '…kosit:…xrechnung…'; Peppol/Factur-X URNs never do.
       An explicit profile overrides the sniff. -->
  <xsl:variable name="profile-resolved" as="xs:string"
      select="if ($profile ne 'auto') then $profile
              else if (contains(lower-case(string(/si:invoice/si:meta/@customization)),
                                'xrechnung')) then 'xrechnung'
              else if (contains(lower-case(string(/si:invoice/si:meta/@customization)),
                                '@aunz')) then 'pint-a-nz'
              else 'generic'"/>

  <!-- ============ i18n ============ -->
  <xsl:variable name="labels"
      select="doc(resolve-uri(concat('../i18n/labels-', $lang, '.xml'), static-base-uri()))"/>

  <!-- A label may be overridden per profile with a "<key>@<profile>" entry, which
       wins over the bare key. Needed because some wording is a JURISDICTION
       property, not a language one: PINT A-NZ calls the tax GST, but an
       English-language German invoice must still say VAT — so labels-en-AU is
       the wrong shape. Same mechanism the xrechnung profile already relies on
       for BT-10. Falls through to the bare key, so nothing changes for profiles
       that declare no override. -->
  <xsl:function name="k:t" as="xs:string">
    <xsl:param name="key" as="xs:string"/>
    <xsl:variable name="scoped"
        select="$labels/labels/label[@key = concat($key, '@', $profile-resolved)]"/>
    <xsl:variable name="base" select="$labels/labels/label[@key = $key]"/>
    <xsl:sequence select="string(($scoped, $base)[1])"/>
  </xsl:function>

  <!-- ============ Number formatting ============ -->
  <!-- Separator convention is a LANGUAGE property; the number of decimal places
       is a CURRENCY property. They were conflated: both picture strings used to
       hard-code two decimals, so a JPY invoice rendered 1500 as "1,500.00" and a
       three-decimal currency (BHD, KWD, OMR…) was silently truncated. The corpus
       could not catch it — every fixture was in EUR. -->
  <xsl:decimal-format name="eu"    decimal-separator="," grouping-separator="."/>
  <xsl:decimal-format name="anglo" decimal-separator="." grouping-separator=","/>
  <!-- French groups with a no-break space (1 500,00), not a period. It used to
       share the German format and would have rendered "1.500,00".
       The PICTURE must use the same U+00A0 the format declares. With a plain
       U+0020 there, Saxon raises "Passive character must not appear between
       active characters in a sub-picture" and every French render dies. That sat
       here undetected because no fixture rendered in French until the French
       locale landed; a French fixture now exercises it. -->
  <xsl:decimal-format name="fr"    decimal-separator="," grouping-separator="&#160;"/>

  <!-- ISO 4217 minor units. The default is 2; only the exceptions are listed. -->
  <xsl:variable name="k:zero-decimal" as="xs:string+" select="(
      'BIF','CLP','DJF','GNF','ISK','JPY','KMF','KRW','PYG','RWF',
      'UGX','UYI','VND','VUV','XAF','XOF','XPF')"/>
  <xsl:variable name="k:three-decimal" as="xs:string+" select="(
      'BHD','IQD','JOD','KWD','LYD','OMR','TND')"/>

  <!-- BT-5, the document currency. Global so k:money can reach it: the function
       is called from deep in the line and totals blocks, where the invoice root
       is not in scope. -->
  <xsl:variable name="currency-code" as="xs:string"
      select="upper-case(normalize-space(string(/si:invoice/si:currency)))"/>
  <xsl:variable name="minor-units" as="xs:integer"
      select="if ($currency-code = $k:zero-decimal) then 0
              else if ($currency-code = $k:three-decimal) then 3
              else 2"/>

  <!-- Grouping/decimal marks per language; decimals per currency. -->
  <xsl:function name="k:format" as="xs:string">
    <xsl:param name="v"/>
    <xsl:param name="places" as="xs:integer"/>
    <xsl:choose>
      <xsl:when test="$lang = 'fr'">
        <xsl:sequence select="format-number(xs:decimal($v),
            concat('#&#160;##0', if ($places = 0) then '' else concat(',', substring('000', 1, $places))), 'fr')"/>
      </xsl:when>
      <xsl:when test="$lang = ('de', 'nl', 'es', 'it')">
        <xsl:sequence select="format-number(xs:decimal($v),
            concat('#.##0', if ($places = 0) then '' else concat(',', substring('000', 1, $places))), 'eu')"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:sequence select="format-number(xs:decimal($v),
            concat('#,##0', if ($places = 0) then '' else concat('.', substring('000', 1, $places))), 'anglo')"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:function>

  <!-- Monetary amounts: decimals follow the document currency. -->
  <xsl:function name="k:money" as="xs:string">
    <xsl:param name="v"/>
    <xsl:sequence select="k:format($v, $minor-units)"/>
  </xsl:function>

  <!-- Quantities are NOT money and must not inherit the currency's minor units:
       routing them through k:money would round a quantity of 1.5 to "2" on a
       zero-decimal invoice. Integers print bare; the rest keep two places. -->
  <xsl:function name="k:qty" as="xs:string">
    <xsl:param name="v"/>
    <xsl:sequence select="if (xs:decimal($v) = floor(xs:decimal($v)))
                          then format-number(xs:decimal($v), '0')
                          else k:format($v, 2)"/>
  </xsl:function>

  <!-- ============ Root ============ -->
  <xsl:template match="/si:invoice">
    <fo:root xmlns:fo="http://www.w3.org/1999/XSL/Format" font-selection-strategy="character-by-character" xsl:use-attribute-sets="page.body">
      <fo:layout-master-set>
        <fo:simple-page-master master-name="invoice"
            page-height="297mm" page-width="210mm"
            margin-top="14mm" margin-bottom="12mm"
            margin-left="20mm" margin-right="16mm">
          <fo:region-body margin-bottom="14mm"/>
          <fo:region-after extent="10mm"/>
        </fo:simple-page-master>
      </fo:layout-master-set>

      <fo:page-sequence master-reference="invoice">
        <fo:static-content flow-name="xsl-region-after">
          <xsl:call-template name="page-footer"/>
        </fo:static-content>

        <fo:flow flow-name="xsl-region-body" xsl:use-attribute-sets="page.body">
          <xsl:call-template name="doc-header"/>
          <xsl:call-template name="party-block"/>
          <xsl:call-template name="meta-strip"/>
          <xsl:apply-templates select="si:lines"/>
          <xsl:apply-templates select="si:allowances-charges"/>
          <xsl:call-template name="totals-block"/>
          <xsl:apply-templates select="si:note"/>
        </fo:flow>
      </fo:page-sequence>
    </fo:root>
  </xsl:template>

  <!-- ============ Document header ============ -->
  <xsl:template name="doc-header">
    <fo:table table-layout="fixed" width="100%">
      <fo:table-column column-width="60%"/>
      <fo:table-column column-width="40%"/>
      <fo:table-body>
        <fo:table-row>
          <fo:table-cell>
            <xsl:choose>
              <xsl:when test="$logo-uri != ''">
                <fo:block>
                  <fo:external-graphic src="{$logo-uri}" content-height="12mm" scaling="uniform"/>
                </fo:block>
              </xsl:when>
              <xsl:otherwise>
                <fo:block xsl:use-attribute-sets="header.sellerName">
                  <xsl:value-of select="si:seller/si:name"/>
                </fo:block>
              </xsl:otherwise>
            </xsl:choose>
          </fo:table-cell>
          <fo:table-cell>
            <fo:block xsl:use-attribute-sets="header.docType">
              <xsl:value-of select="k:t(if (si:meta/@type-code = '381')
                                        then 'doc.creditnote' else 'doc.invoice')"/>
            </fo:block>
          </fo:table-cell>
        </fo:table-row>
      </fo:table-body>
    </fo:table>
    <fo:block xsl:use-attribute-sets="header.rule"/>
  </xsl:template>

  <!-- ============ Invoice meta strip ============ -->
  <xsl:template name="meta-strip">
    <fo:table table-layout="fixed" width="100%" space-before="5mm">
      <fo:table-column column-width="25%"/>
      <fo:table-column column-width="25%"/>
      <fo:table-column column-width="25%"/>
      <fo:table-column column-width="25%"/>
      <fo:table-body>
        <fo:table-row>
          <xsl:call-template name="meta-cell">
            <xsl:with-param name="label" select="k:t('meta.number')"/>
            <xsl:with-param name="value" select="si:number"/>
          </xsl:call-template>
          <xsl:call-template name="meta-cell">
            <xsl:with-param name="label" select="k:t('meta.issued')"/>
            <xsl:with-param name="value" select="si:issue-date"/>
          </xsl:call-template>
          <xsl:call-template name="meta-cell">
            <xsl:with-param name="label" select="k:t('meta.due')"/>
            <xsl:with-param name="value" select="si:due-date"/>
          </xsl:call-template>
          <xsl:choose>
            <xsl:when test="si:preceding-invoice">
              <xsl:call-template name="meta-cell">
                <xsl:with-param name="label" select="k:t('meta.credits')"/>
                <xsl:with-param name="value" select="si:preceding-invoice[1]"/>
              </xsl:call-template>
            </xsl:when>
            <xsl:when test="$profile-resolved = 'xrechnung' and si:buyer-reference">
              <!-- XRechnung: BT-10 is the Leitweg-ID the buyer routes on —
                   label it as such and give it accent weight (never fall
                   back to the order reference under this profile). -->
              <xsl:call-template name="meta-cell">
                <xsl:with-param name="label" select="k:t('meta.leitweg')"/>
                <xsl:with-param name="value" select="si:buyer-reference"/>
                <xsl:with-param name="accent" select="true()"/>
              </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
              <xsl:call-template name="meta-cell">
                <xsl:with-param name="label" select="k:t('meta.reference')"/>
                <xsl:with-param name="value" select="(si:buyer-reference, si:order-reference)[1]"/>
              </xsl:call-template>
            </xsl:otherwise>
          </xsl:choose>
        </fo:table-row>
      </fo:table-body>
    </fo:table>
  </xsl:template>

  <xsl:template name="meta-cell">
    <xsl:param name="label"/>
    <xsl:param name="value"/>
    <xsl:param name="accent" select="false()"/>
    <fo:table-cell padding-right="3mm">
      <xsl:choose>
        <xsl:when test="normalize-space(string($value)) != ''">
          <fo:block xsl:use-attribute-sets="label"><xsl:value-of select="$label"/></fo:block>
          <fo:block xsl:use-attribute-sets="meta.value">
            <xsl:choose>
              <xsl:when test="$accent">
                <fo:inline xsl:use-attribute-sets="accent"><xsl:value-of select="$value"/></fo:inline>
              </xsl:when>
              <xsl:otherwise><xsl:value-of select="$value"/></xsl:otherwise>
            </xsl:choose>
          </fo:block>
        </xsl:when>
        <xsl:otherwise>
          <fo:block/>  <!-- fo:table-cell requires (%block;)+ — never emit an empty cell -->
        </xsl:otherwise>
      </xsl:choose>
    </fo:table-cell>
  </xsl:template>

  <!-- ============ Document-level allowances & charges (BG-20/21) ============ -->
  <xsl:template match="si:allowances-charges">
    <fo:table table-layout="fixed" width="100%" space-before="1.5mm">
      <fo:table-column column-width="59%"/>
      <fo:table-column column-width="14%"/>
      <fo:table-column column-width="10%"/>
      <fo:table-column column-width="17%"/>
      <fo:table-body>
        <xsl:for-each select="si:item">
          <fo:table-row>
            <fo:table-cell xsl:use-attribute-sets="lines.cell">
              <fo:block>
                <xsl:value-of select="k:t(concat('ac.', @kind))"/>
                <xsl:if test="@reason != ''">
                  <xsl:text> — </xsl:text><xsl:value-of select="@reason"/>
                </xsl:if>
              </fo:block>
            </fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="lines.cell"><fo:block/></fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="lines.cellNum">
              <fo:block><xsl:value-of select="si:vat/@rate"/>%</fo:block>
            </fo:table-cell>
            <fo:table-cell xsl:use-attribute-sets="lines.cellNum">
              <fo:block>
                <xsl:value-of select="if (@kind = 'allowance') then '-' else '+'"/>
                <xsl:value-of select="k:money(si:amount)"/>
              </fo:block>
            </fo:table-cell>
          </fo:table-row>
        </xsl:for-each>
      </fo:table-body>
    </fo:table>
  </xsl:template>

  <!-- ============ Free-text notes ============ -->
  <xsl:template match="si:note">
    <fo:block space-before="5mm" font-size="8pt" color="#5A5F68">
      <xsl:value-of select="."/>
    </fo:block>
  </xsl:template>

  <!-- ============ Footer ============ -->
  <xsl:template name="page-footer">
    <fo:block xsl:use-attribute-sets="footer">
      <fo:table table-layout="fixed" width="100%">
        <fo:table-column column-width="40%"/>
        <fo:table-column column-width="30%"/>
        <fo:table-column column-width="30%"/>
        <fo:table-body>
          <fo:table-row>
            <fo:table-cell>
              <fo:block><xsl:value-of select="/si:invoice/si:seller/si:name"/>
                <xsl:if test="/si:invoice/si:seller/si:vat-id">
                  <xsl:text> · </xsl:text><xsl:value-of select="/si:invoice/si:seller/si:vat-id"/>
                </xsl:if>
              </fo:block>
            </fo:table-cell>
            <fo:table-cell>
              <fo:block text-align="center">
                <xsl:value-of select="k:t('meta.number')"/><xsl:text> </xsl:text>
                <xsl:value-of select="/si:invoice/si:number"/>
              </fo:block>
            </fo:table-cell>
            <fo:table-cell>
              <fo:block text-align="right">
                <xsl:value-of select="k:t('footer.page')"/><xsl:text> </xsl:text>
                <fo:page-number/><xsl:text> / </xsl:text>
                <fo:page-number-citation-last ref-id="faktorei-doc-end"/>
              </fo:block>
            </fo:table-cell>
          </fo:table-row>
        </fo:table-body>
      </fo:table>
    </fo:block>
  </xsl:template>

</xsl:stylesheet>

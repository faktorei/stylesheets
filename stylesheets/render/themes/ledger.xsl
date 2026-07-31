<?xml version="1.0" encoding="UTF-8"?>
<!--
  faktorei · themes/ledger.xsl — the default theme ("designed to look correct
  in a tax auditor's hands").

  THEMING CONTRACT: themes contain xsl:attribute-set definitions and theme
  tunables ONLY — never templates, never structure. Every attribute-set name
  in this file is stable public API; custom themes override any subset by
  importing this file and redefining sets. Structural change belongs in a
  services engagement, not a theme.

  Starter fonts are the FOP base-14 set (Helvetica) so the pipeline runs with
  zero font setup. Production deployments register Source Sans 3 + IBM Plex
  Mono in fop.xconf and override ledger.font-* accordingly; amounts should
  always use a tabular-numeral face.

  License: Apache-2.0
-->
<xsl:stylesheet version="3.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:fo="http://www.w3.org/1999/XSL/Format">

  <!-- ============ Theme tunables ============ -->
  <xsl:param name="theme.accent"     select="'#2A4B8D'"/>  <!-- giro-blue; customer-brandable -->
  <xsl:param name="theme.ink"        select="'#22252B'"/>  <!-- carbon -->
  <xsl:param name="theme.ink-soft"   select="'#5A5F68'"/>
  <xsl:param name="theme.zebra"      select="'#F1F4F0'"/>  <!-- duplicate-leaf at low strength -->
  <xsl:param name="theme.rule"       select="'#22252B'"/>
  <xsl:param name="theme.font-body"  select="'Helvetica'"/>
  <xsl:param name="theme.font-data"  select="'Helvetica'"/> <!-- prod: IBM Plex Mono -->

  <!-- ============ Page ============ -->
  <xsl:attribute-set name="page.body">
    <xsl:attribute name="font-family"><xsl:value-of select="$theme.font-body"/></xsl:attribute>
    <xsl:attribute name="font-size">9pt</xsl:attribute>
    <xsl:attribute name="line-height">1.45</xsl:attribute>
    <xsl:attribute name="color"><xsl:value-of select="$theme.ink"/></xsl:attribute>
  </xsl:attribute-set>

  <!-- ============ Header block ============ -->
  <xsl:attribute-set name="header.docType">
    <xsl:attribute name="font-size">20pt</xsl:attribute>
    <xsl:attribute name="font-weight">bold</xsl:attribute>
    <xsl:attribute name="letter-spacing">0.08em</xsl:attribute>
    <xsl:attribute name="text-align">right</xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="header.sellerName">
    <xsl:attribute name="font-size">13pt</xsl:attribute>
    <xsl:attribute name="font-weight">bold</xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="header.rule">
    <xsl:attribute name="border-bottom">2pt solid <xsl:value-of select="$theme.rule"/></xsl:attribute>
    <xsl:attribute name="margin-top">4mm</xsl:attribute>
    <xsl:attribute name="margin-bottom">6mm</xsl:attribute>
  </xsl:attribute-set>

  <!-- ============ Labels & meta ============ -->
  <xsl:attribute-set name="label">
    <xsl:attribute name="font-size">6.5pt</xsl:attribute>
    <xsl:attribute name="letter-spacing">0.09em</xsl:attribute>
    <xsl:attribute name="text-transform">uppercase</xsl:attribute>
    <xsl:attribute name="color"><xsl:value-of select="$theme.ink-soft"/></xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="meta.value">
    <xsl:attribute name="font-family"><xsl:value-of select="$theme.font-data"/></xsl:attribute>
    <xsl:attribute name="font-size">9pt</xsl:attribute>
  </xsl:attribute-set>

  <!-- ============ Line-item table ============ -->
  <xsl:attribute-set name="lines.table">
    <xsl:attribute name="table-layout">fixed</xsl:attribute>
    <xsl:attribute name="width">100%</xsl:attribute>
    <xsl:attribute name="space-before">6mm</xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="lines.headerCell">
    <xsl:attribute name="font-size">6.5pt</xsl:attribute>
    <xsl:attribute name="letter-spacing">0.09em</xsl:attribute>
    <xsl:attribute name="text-transform">uppercase</xsl:attribute>
    <xsl:attribute name="color"><xsl:value-of select="$theme.ink-soft"/></xsl:attribute>
    <xsl:attribute name="border-bottom">0.8pt solid <xsl:value-of select="$theme.rule"/></xsl:attribute>
    <xsl:attribute name="padding">1.4mm 1.5mm</xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="lines.cell">
    <xsl:attribute name="padding">1.6mm 1.5mm</xsl:attribute>
    <xsl:attribute name="font-size">8.5pt</xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="lines.cellNum" use-attribute-sets="lines.cell">
    <xsl:attribute name="text-align">right</xsl:attribute>
    <xsl:attribute name="font-family"><xsl:value-of select="$theme.font-data"/></xsl:attribute>
  </xsl:attribute-set>

  <!-- Position number: data font but LEFT-aligned, matching the left "POS"
       heading (amounts stay right-aligned via lines.cellNum). -->
  <xsl:attribute-set name="lines.cellPos" use-attribute-sets="lines.cell">
    <xsl:attribute name="text-align">left</xsl:attribute>
    <xsl:attribute name="font-family"><xsl:value-of select="$theme.font-data"/></xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="lines.rowZebra">
    <xsl:attribute name="background-color"><xsl:value-of select="$theme.zebra"/></xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="lines.broughtRow">
    <xsl:attribute name="font-size">7.5pt</xsl:attribute>
    <xsl:attribute name="color"><xsl:value-of select="$theme.ink-soft"/></xsl:attribute>
    <xsl:attribute name="padding">0mm 1.5mm</xsl:attribute>
  </xsl:attribute-set>

  <!-- ============ VAT breakdown & totals ============ -->
  <xsl:attribute-set name="totals.block">
    <xsl:attribute name="keep-together.within-page">always</xsl:attribute>
    <xsl:attribute name="space-before">7mm</xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="totals.cell">
    <xsl:attribute name="padding">1.2mm 1.5mm</xsl:attribute>
    <xsl:attribute name="font-size">9pt</xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="totals.cellNum" use-attribute-sets="totals.cell">
    <xsl:attribute name="text-align">right</xsl:attribute>
    <xsl:attribute name="font-family"><xsl:value-of select="$theme.font-data"/></xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="totals.dueRow">
    <xsl:attribute name="font-weight">bold</xsl:attribute>
    <xsl:attribute name="font-size">10.5pt</xsl:attribute>
    <xsl:attribute name="border-top">1.4pt solid <xsl:value-of select="$theme.rule"/></xsl:attribute>
    <xsl:attribute name="border-bottom">1.4pt solid <xsl:value-of select="$theme.rule"/></xsl:attribute>
  </xsl:attribute-set>

  <xsl:attribute-set name="accent">
    <xsl:attribute name="color"><xsl:value-of select="$theme.accent"/></xsl:attribute>
  </xsl:attribute-set>

  <!-- ============ Footer ============ -->
  <xsl:attribute-set name="footer">
    <xsl:attribute name="font-size">7pt</xsl:attribute>
    <xsl:attribute name="color"><xsl:value-of select="$theme.ink-soft"/></xsl:attribute>
    <xsl:attribute name="border-top">0.4pt solid <xsl:value-of select="$theme.ink-soft"/></xsl:attribute>
    <xsl:attribute name="padding-top">1.5mm</xsl:attribute>
  </xsl:attribute-set>

</xsl:stylesheet>

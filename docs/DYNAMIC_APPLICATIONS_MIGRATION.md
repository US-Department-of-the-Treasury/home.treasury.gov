# Dynamic Applications Migration Plan

**Created:** January 18, 2026  
**Status:** Planning  
**Priority:** Phase 2 (Post-Initial Launch)

---

## Executive Summary

The Hugo migration successfully migrated **16,500+ static content pages** including all news articles, policy pages, and informational content. However, several **dynamic data applications** on Treasury.gov require server-side rendering, database queries, or external API integrations that are incompatible with static site generation.

This document outlines:
1. What dynamic applications exist
2. Why they weren't included in Phase 1
3. Migration options for each
4. Recommended approach and timeline

---

## Dynamic Applications Inventory

### 1. Interest Rate Data Views (Data Chart Center)

**Current URLs:** `home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=*`

| Data Type | Example URL | Update Frequency |
|-----------|-------------|------------------|
| Daily Treasury Yield Curve | `TextView?type=daily_treasury_yield_curve` | Daily |
| Daily Treasury Bill Rates | `TextView?type=daily_treasury_bill_rates` | Daily |
| Daily Treasury Long-Term Rates | `TextView?type=daily_treasury_long_term_rate` | Daily |
| Daily Treasury Real Yield Curve | `TextView?type=daily_treasury_real_long_term` | Daily |
| Daily Treasury Par Yield Curve | `TextView?type=daily_treasury_par_yield_curve` | Daily |

**Dynamic Features:**
- Query parameter filtering (`?type=`, `?field_tdr_date_value=`)
- Date range selection (monthly views)
- Multiple output formats (HTML table, XML, CSV)
- Daily data updates from backend system

**Why Not Migrated:**
- Requires database backend for daily rate data
- Query parameters can't be handled by static HTML
- ~117 unique URL patterns with date/type combinations

**Current Status on Live Site:**
- Some TextView pages returning "Internal Error" (data volume issues)
- Treasury has migrated data to new endpoints (CSV archives, XML feeds)
- Fiscal Data Portal (`fiscaldata.treasury.gov`) provides modern API access

---

### 2. TARP (Troubled Assets Relief Program) Data Tables

**Current URLs:** `home.treasury.gov/data/troubled-assets-relief-program/*`

| Section | Est. URLs | Features |
|---------|-----------|----------|
| CPP Results | 800+ | Sortable by institution, state, amount, type |
| Bank Lending | 100+ | Paginated tables |
| Contracts | 100+ | Paginated tables |
| Housing Programs | 500+ | Multiple sub-sections |

**Dynamic Features:**
- Server-side pagination (`?page=0`, `?page=1`, etc.)
- Multi-column sorting (`?order=field_amount&sort=asc`)
- Combined pagination + sorting (creates hundreds of URL permutations)

**Why Not Migrated:**
- ~1,710 URLs with query parameter variations
- Historical data (2008-2014 financial crisis)
- Would require rebuilding sortable table functionality

**Data Characteristics:**
- Data is **frozen** (historical, no longer updated)
- Could potentially be pre-rendered as static HTML
- Alternatively, client-side JavaScript sorting is viable

---

### 3. TIC (Treasury International Capital) System Data

**Current URLs:** `home.treasury.gov/resource-center/data-chart-center/tic/*`

| Data Type | Description |
|-----------|-------------|
| Foreign Holdings | U.S. securities held by foreign entities |
| Capital Flows | Cross-border financial transactions |
| Historical Tables | Time series data |

**Dynamic Features:**
- Data table rendering
- Some query parameter filtering
- Links to downloadable data files (already available)

**Why Not Migrated:**
- ~50 URLs with data table functionality
- Some pages are static (can be migrated as-is)
- Data-heavy pages need evaluation

---

### 4. Power BI Dashboard Embeds

**Current Status:** ~15 embedded Power BI Government dashboards

These are **not migrations** — they're external embeds hosted on `app.high.powerbigov.us`. The Hugo site only needs to:
- Create container pages with iframe embeds
- Maintain embed URLs

**No additional resources required** — just documentation of embed URLs.

---

### 5. External Portals (Out of Scope)

These are **separate applications** hosted on different domains:

| Portal | Domain | Notes |
|--------|--------|-------|
| OFAC Sanctions Search | `sanctionssearch.ofac.treas.gov` | Full search application |
| Fiscal Data Portal | `fiscaldata.treasury.gov` | Modern data API |
| TreasuryDirect | `treasurydirect.gov` | Bond purchasing system |
| FinCEN | `fincen.gov` | Separate bureau site |
| CARES Act Portal | `portal.treasury.gov/cares/` | Compliance system |
| BSA E-Filing | `bsaefiling.fincen.treas.gov` | Forms submission |

**Action:** Link to these portals from Hugo site — no migration needed.

---

## Migration Options Analysis

### Option A: Link to Modern Data Sources (Recommended for Interest Rates)

**Approach:** Redirect users to Treasury's modern data infrastructure.

**Implementation:**
1. Create landing pages in Hugo explaining data availability
2. Link to:
   - CSV/XML Archives: `home.treasury.gov/interest-rates-data-csv-archive`
   - Fiscal Data Portal: `fiscaldata.treasury.gov`
   - Data.gov catalog: `catalog.data.gov/dataset/daily-treasury-*`

**Pros:**
- No development effort
- Users get modern, maintained data access
- Treasury has already invested in these platforms

**Cons:**
- Different UX than legacy TextView pages
- May require user education

**Effort:** 1-2 days

---

### Option B: Client-Side JavaScript Data Application

**Approach:** Build a JavaScript application that fetches data from Treasury APIs and renders tables/charts client-side.

**Implementation:**
1. Create JavaScript module in `themes/treasury/assets/js/`
2. Fetch data from Treasury XML/CSV endpoints
3. Render sortable/filterable tables with vanilla JS or lightweight library
4. Handle date range selection

**Example Architecture:**
```
/resource-center/data-chart-center/interest-rates/
├── _index.md (Hugo landing page)
├── daily-rates.md (Hugo page with JS hooks)
└── [JavaScript handles filtering/display]
```

**Pros:**
- Replicates legacy functionality
- Works within Hugo static site
- CSP-compliant (external scripts from 'self')

**Cons:**
- Development effort (2-4 weeks)
- Requires ongoing maintenance
- API dependency on Treasury data feeds

**Effort:** 2-4 weeks

---

### Option C: Pre-Render Static Tables (Recommended for TARP)

**Approach:** For historical/frozen data like TARP, pre-generate all table permutations as static HTML.

**Implementation:**
1. Fetch all TARP data from current Drupal site
2. Generate static Hugo pages for each sort/page combination
3. Use client-side JavaScript for in-page sorting (optional enhancement)

**Pros:**
- Data is frozen (no updates needed)
- Full static site benefits (fast, cacheable)
- One-time effort

**Cons:**
- Large number of pages to generate
- Some URL patterns may need redirects

**Effort:** 1-2 weeks

---

### Option D: Hybrid Static + JavaScript

**Approach:** Pre-render data as JSON, use client-side JavaScript for sorting/filtering.

**Implementation:**
1. Generate JSON data files during Hugo build
2. Create JavaScript table component
3. Load JSON and render sortable tables client-side

**Pros:**
- Best of both worlds
- Fast initial load (static JSON)
- Rich interactivity (JS sorting/filtering)

**Cons:**
- More complex implementation
- Requires JavaScript for full functionality

**Effort:** 2-3 weeks

---

## Recommended Migration Plan

### Phase 2A: Interest Rate Data (Week 1-2)

| Task | Approach | Effort |
|------|----------|--------|
| Create Data Chart Center landing page | Option A | 2 hours |
| Document all data sources with links | Static content | 4 hours |
| Add redirect rules for legacy TextView URLs | Akamai config | 2 hours |
| Create "Interest Rates" section with data links | Static content | 4 hours |

**Deliverable:** Users can access all interest rate data via modern sources.

---

### Phase 2B: TARP Historical Data (Week 3-4)

| Task | Approach | Effort |
|------|----------|--------|
| Scrape all TARP table data | Python script | 8 hours |
| Generate static Hugo pages | Python/Hugo | 16 hours |
| Implement client-side sorting (enhancement) | JavaScript | 8 hours |
| Set up redirects for legacy URLs | Akamai config | 4 hours |

**Deliverable:** All TARP data accessible as static pages with optional JS sorting.

---

### Phase 2C: TIC Data & Power BI (Week 5)

| Task | Approach | Effort |
|------|----------|--------|
| Audit TIC pages for static vs. dynamic | Analysis | 4 hours |
| Migrate static TIC pages to Hugo | Content | 8 hours |
| Create Power BI embed pages | Hugo templates | 4 hours |
| Link to external TIC data sources | Static content | 2 hours |

**Deliverable:** TIC section migrated, Power BI dashboards embedded.

---

## Resource Requirements

| Resource | Phase 2A | Phase 2B | Phase 2C | Total |
|----------|----------|----------|----------|-------|
| Frontend Developer | 1 day | 3 days | 1 day | **5 days** |
| Content Editor | 0.5 days | 1 day | 0.5 days | **2 days** |
| DevOps (Akamai) | 0.25 days | 0.5 days | 0.25 days | **1 day** |

**Total Effort:** ~8 person-days over 5 weeks

---

## Success Criteria

1. **Interest Rates:** Users can access daily rate data within 2 clicks from homepage
2. **TARP:** All historical TARP data searchable/viewable
3. **No 404s:** Legacy URLs redirect to appropriate new locations
4. **Performance:** All pages load in < 3 seconds
5. **Accessibility:** All data tables meet 508 compliance

---

## Appendix: URL Inventory

### Interest Rate TextView URLs (Sample)

```
/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve
/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_bill_rates
/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_long_term_rate
/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_real_long_term
/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_par_yield_curve
/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_par_real_yield_curve
```

### TARP Query Parameter Patterns

```
?page=0
?page=1&order=field_amount&sort=asc
?page=2&order=field_institution&sort=desc
?order=field_state&sort=asc
... (hundreds of combinations)
```

### Modern Data Sources (Replacements)

| Legacy | Modern Replacement |
|--------|-------------------|
| TextView pages | `fiscaldata.treasury.gov/datasets/` |
| XML buttons | `home.treasury.gov/interest-rates-data-csv-archive` |
| Data Chart Center | `fiscaldata.treasury.gov/americas-finance-guide/` |

---

## Related Documents

- [Migration Analysis](./MIGRATION_ANALYSIS.md)
- [Migration Checklist](../MIGRATION_CHECKLIST.md)
- [Testing Instructions](./TESTING_INSTRUCTIONS.md)

---

*Last Updated: January 18, 2026*

# Hallucination Audit Report

**Generated:** 2026-01-20T07:18:57.872804

## Executive Summary

| Metric | Count |
|--------|-------|
| Total Files Audited | 124 |
| OK (content matches) | 97 |
| Content Mismatch | 9 |
| Not Found on Live Site | 18 |
| Errors | 0 |
| **HALLUCINATIONS** | **5** |

## Detected Hallucinations

These files contain content that does NOT exist on the live Treasury.gov site:

### `content/policy-issues/financing-the-government/quarterly-refunding.md`

- **URL:** /policy-issues/financing-the-government/quarterly-refunding/
- **Similarity to Live:** 27.3%
- **Local Title:** Treasury Quarterly Refunding
- **Live Title:** Treasury Quarterly Refunding

**Local Content Preview:**
```
treasury quarterly refunding changes in debt management policy are generally informed by and communicated through the quarterly refunding process near the middle of each calendar quarter. quarterly refunding process a summary of the treasury quarterly refunding process. most recent quarterly refundi...
```

**Live Content Preview:**
```
treasury quarterly refunding changes in debt management policy are generally informed by and communicated through the quarterly refunding process near the middle of each calendar quarter. a summary of the treasury quarterly refunding process. most recent quarterly refunding documents treasury releas...
```

---

### `content/about/budget-financial-reporting-planning-and-performance/inspector-general-audits-and-investigative-reports.md`

- **URL:** /about/budget-financial-reporting-planning-and-performance/inspector-general-audits-and-investigative-reports/
- **Similarity to Live:** 0.5%
- **Local Title:** Inspector General Audits and Investigative Reports
- **Live Title:** Inspector General Audits and Investigative Reports

**Local Content Preview:**
```
inspector general audits and investigative reports office of inspector general reports treasury inspector general for tax administration reports special inspector general for troubled assets relief program reports...
```

**Live Content Preview:**
```
here’s how you know u.s. department of the treasury about treasury policy issues data services news year in review working families tax cuts home about budget, financial reporting, planning and performance inspector general audits and investigative reports general information offices bureaus budget,...
```

---

### `content/services/taxes.md`

- **URL:** /services/taxes
- **Similarity to Live:** 6.5%
- **Local Title:** Taxes
- **Live Title:** Taxes

**Local Content Preview:**
```
taxes internal revenue service (irs) website irs forms and publications refund status irs withholding calculator foreign account tax compliance act...
```

**Live Content Preview:**
```
here’s how you know u.s. department of the treasury about treasury policy issues data services news year in review working families tax cuts report fraud waste and abuse bonds and securities treasury financial assistance treasury payments currency and coins treasury auctions the multiemployer pensio...
```

---

### `content/services/forms.md`

- **URL:** /services/forms
- **Similarity to Live:** 19.6%
- **Local Title:** Forms
- **Live Title:** Forms

**Local Content Preview:**
```
forms irs forms and instructions savings bonds and treasury securities forms bank secrecy act forms treasury international capital (tic) forms and instructions alcohol and tobacco tax and trade bureau (ttb) forms office of the comptroller of the currency forms usa.gov/forms...
```

**Live Content Preview:**
```
here’s how you know u.s. department of the treasury about treasury policy issues data services news year in review working families tax cuts report fraud waste and abuse bonds and securities treasury financial assistance treasury payments currency and coins treasury auctions the multiemployer pensio...
```

---

### `content/about/general-information/organizational-chart.md`

- **URL:** /about/general-information/organizational-chart
- **Similarity to Live:** 2.7%
- **Local Title:** Organizational Chart
- **Live Title:** Organizational Chart

**Local Content Preview:**
```
organizational chart...
```

**Live Content Preview:**
```
here’s how you know u.s. department of the treasury about treasury policy issues data services news year in review working families tax cuts home about general information organizational chart general information role of the treasury officials organizational chart orders and directives offices burea...
```

---

## Content Mismatches (Non-Hallucination)

These files have some content differences but may not be hallucinations:

| File | Similarity | Local Title | Live Title |
|------|------------|-------------|------------|
| `content/policy-issues/financial-markets-financial-institutions-and-fiscal-service.md` | 36.6% | Financial Markets, Financial I... | Financial Markets, Financial I... |
| `content/about/budget-financial-reporting-planning-and-performance/agency-financial-report.md` | 34.5% | Agency Financial Report | Agency Financial Report |
| `content/services/treasury-payments.md` | 52.1% | Treasury Payments | Treasury Payments |
| `content/services/bonds-and-securities.md` | 37.1% | Bonds and Securities | Bonds and Securities |

## Pages Not Found on Live Site

These local files have no corresponding page on the live site (may be new or generated content):

- `content/policy-issues/small-business-programs/cdfi-fund.md` → /policy-issues/small-business-programs/cdfi-fund
- `content/policy-issues/terrorism-and-illicit-finance/sanctions.md` → /policy-issues/terrorism-and-illicit-finance/sanctions
- `content/data/treasury-coupon-issues-and-corporate-bond-yield-curves.md` → /data/treasury-coupon-issues-and-corporate-bond-yield-curves/ (soft 404)
- `content/policy-issues/financing-the-government/debt-management.md` → /policy-issues/financing-the-government/debt-management
- `content/footer/privacy-policy.md` → /footer/privacy-policy/
- `content/data/troubled-assets-relief-program/housing.md` → /data/troubled-assets-relief-program/housing/ (soft 404)
- `content/footer/faqs.md` → /footer/faqs/
- `content/footer/site-policies.md` → /footer/site-policies/
- `content/footer/google-privacy.md` → /footer/google-privacy/
- `content/policy-issues/coronavirus/assistance-for-american-industry.md` → /policy-issues/coronavirus/assistance-for-american-industry/ (soft 404)
- `content/resource-center/data-chart-center.md` → /resource-center/data-chart-center
- `content/policy-issues/economic-policy/social-security-and-medicare.md` → /policy-issues/economic-policy/social-security-and-medicare/
- `content/utility/accessibility.md` → /utility/accessibility/ (soft 404)
- `content/policy-issues/tax-policy/overview.md` → /policy-issues/tax-policy/overview
- `content/about/careers-at-treasury/how-to-apply.md` → /about/careers-at-treasury/how-to-apply/ (soft 404)
- `content/policy-issues/tax-policy/tax-policy-overview.md` → /policy-issues/tax-policy/tax-policy-overview/
- `content/policy-issues/financial-markets-financial-institutions-and-fiscal-service/pay-for-results-sippra.md` → /policy-issues/financial-markets-financial-institutions-and-fiscal-service/pay-for-results-sippra/
- `content/services/report-fraud-waste-and-abuse.md` → /services/report-fraud-waste-and-abuse (soft 404)

## Recommendations

1. **Hallucinations**: Delete or replace these files - they contain AI-generated content not from the live site.

2. **Not Found**: Review whether these are:
   - New content to be published
   - Placeholder/template content that should be removed
   - Pages that were removed from the live site

3. **Content Mismatches**: Review for accuracy - may be intentional updates or need re-scraping.

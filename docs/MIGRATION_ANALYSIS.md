# Treasury.gov URL Migration Analysis

## Summary

**Total URLs in `all_tres_urls.md`:** 43,943 lines  
**Total `home.treasury.gov` URLs:** 37,009  

---

## URL Categories

### 1. STATIC ASSETS (system/files) - 15,380 URLs
These are document/media files hosted on Drupal. Need to be migrated to S3/CDN.

| File Type | Count |
|-----------|-------|
| PDF       | 13,156 |
| XLSX      | 894 |
| JPG       | 393 |
| PNG       | 392 |
| XLS       | 234 |
| PDF (uppercase) | 97 |
| ZIP       | 50 |
| DOCX      | 39 |
| CSV       | 33 |
| Other     | ~92 |

**Action:** Copy to S3, maintain URL structure or set up redirects.

---

### 2. NEWS CONTENT - 17,106 URLs

| Section | Drupal URLs | Hugo Content | Gap |
|---------|-------------|--------------|-----|
| press-releases | 15,106 | 13,159 | **1,947 missing** |
| featured-stories | 165 | 162 | 3 missing |
| readouts | 3 | 865 | ✅ Hugo has more |
| statements-remarks | (in press) | 454 | ✅ Already migrated |
| testimonies | (in press) | 89 | ✅ Already migrated |
| media-advisories | 769 | 0 | **769 to add** |
| weekly-public-schedule | 715 | 0 | **715 to add** |
| weekly-schedule-updates | 160 | 0 | **160 to add** |
| recent-highlights | 23 | 0 | **23 to add** |
| webcasts | 10 | 1 | 9 to add |

**Priority Actions:**
1. ✅ Migrate remaining ~1,947 press-releases
2. 🔲 Add media-advisories section (769 items)
3. 🔲 Add weekly-public-schedule section (715 items)
4. 🔲 Add weekly-schedule-updates section (160 items)

---

### 3. DATA SECTION - 2,490 URLs

| Subsection | Count |
|------------|-------|
| troubled-assets-relief-program (TARP) | 1,710 |
| us-international-reserve-position | 719 |
| treasury-international-capital-tic-system | 50 |
| Other | 11 |

**Note:** These are data-heavy pages, likely with dynamic elements. Evaluate for Hugo suitability.

---

### 4. ABOUT SECTION - 692 URLs

| Subsection | Count |
|------------|-------|
| general-information | 399 |
| history | 135 |
| budget-financial-reporting | 62 |
| offices | 57 |
| careers-at-treasury | 34 |
| Other | 5 |

---

### 5. POLICY-ISSUES SECTION - 571 URLs

| Subsection | Count |
|------------|-------|
| coronavirus | 201 |
| financial-markets | 77 |
| international | 63 |
| small-business-programs | 58 |
| consumer-policy | 57 |
| covid19-economic-relief | 40 |
| financing-the-government | 31 |
| terrorism-and-illicit-finance | 14 |
| tax-policy | 13 |
| Other | 17 |

---

### 6. RESOURCE-CENTER - 121 URLs

| Subsection | Count |
|------------|-------|
| data-chart-center | 117 |
| sb-programs | 4 |

---

### 7. SERVICES - 91 URLs

| Subsection | Count |
|------------|-------|
| multiemployer-pension-reform-act | 51 |
| tours-and-library | 8 |
| treasury-financial-assistance | 7 |
| government-shared-services | 7 |
| Other | 18 |

---

### 8. DRUPAL INFRASTRUCTURE (SKIP) - 330 URLs

| Path | Count | Action |
|------|-------|--------|
| sites/ | 125 | Skip - Drupal assets |
| themes/ | 91 | Skip - Drupal theme |
| libraries/ | 87 | Skip - Drupal libs |
| modules/ | 14 | Skip - Drupal modules |
| core/ | 13 | Skip - Drupal core |

---

### 9. MISCELLANEOUS - ~100 URLs

- faq-item: 56
- footer: 29
- utility: 17
- subfooter: 10
- wftc: 10
- cfius-faq-item: 3
- Various one-off pages

---

## Migration Priority Matrix

### Phase 1: Complete News Migration (HIGH PRIORITY)
- [ ] Scrape remaining 1,947 press-releases
- [ ] Create media-advisories content type
- [ ] Create weekly-schedule content types

### Phase 2: Static Assets (HIGH PRIORITY)  
- [ ] Inventory all 15,380 files in system/files
- [ ] Set up S3 bucket for static assets
- [ ] Create URL mapping/redirect plan

### Phase 3: About & Policy Pages (MEDIUM PRIORITY)
- [ ] Evaluate about section for Hugo migration
- [ ] Evaluate policy-issues section
- [ ] Determine which need dynamic features

### Phase 4: Data & Resource Center (LOWER PRIORITY)
- [ ] Assess TARP/data pages complexity
- [ ] Determine if data pages need server-side rendering

---

## Recommended Next Steps

1. **Run gap analysis script** to identify exactly which press-releases are missing
2. **Create scraper** for media-advisories and schedule content
3. **Set up asset migration pipeline** for system/files
4. **Create URL redirect map** for Akamai configuration

---

*Generated: 2026-01-16*

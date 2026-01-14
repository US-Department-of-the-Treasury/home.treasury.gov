# Akamai Integration Guide for Treasury Hugo Site

This document provides configuration details for integrating the Hugo static site with the existing Drupal site via Akamai path-based routing.

---

## Overview

| Component | Description |
|-----------|-------------|
| **Primary Domain** | `home.treasury.gov` |
| **Legacy Origin** | Drupal CMS (existing) |
| **New Origin** | Hugo static site on S3 |
| **Routing** | Path-based via Akamai |

The Hugo site serves a subset of URLs; all other traffic continues to the legacy Drupal origin.

---

## Origin Configuration

### Hugo Origin (New)

| Setting | Value |
|---------|-------|
| Origin Type | S3 Bucket (or S3 Website Endpoint) |
| Origin Hostname | `treasury-hugo-prod.s3.amazonaws.com` |
| Origin Protocol | HTTPS |
| Forward Host Header | Origin Hostname |
| Cache Key | Include path and query string |

### Drupal Origin (Existing)

No changes required to existing Drupal origin configuration.

---

## Path Routing Rules

### Routes to Hugo Origin

Configure these path patterns to route to the Hugo S3 origin:

```
# Press Releases Section
/news/press-releases/
/news/press-releases/index.html
/news/press-releases/page/*
/news/press-releases/sb0337/
/news/press-releases/sb0338/
/news/press-releases/sb0339/
/news/press-releases/sb0340/
/news/press-releases/sb0341/
/news/press-releases/sb0342/
/news/press-releases/sb0343/
/news/press-releases/sb0344/
/news/press-releases/sb0345/
/news/press-releases/sb0346/
/news/press-releases/sb0347/
/news/press-releases/sb0348/
/news/press-releases/sb0349/
/news/press-releases/sb0350/
/news/press-releases/sb0351/
/news/press-releases/sb0352/
/news/press-releases/sb0353/
/news/press-releases/sb0354/
/news/press-releases/sb0355/
/news/press-releases/sb0356/
/news/press-releases/sb0357/

# Static Assets (scoped to Hugo)
/css/treasury.css
/css/uswds.min.css
/js/treasury.js
/js/uswds.min.js
/images/treasury-seal.svg
/images/treasury-seal-green.png
/images/flag-favicon-57.png
/images/us_flag_small.png
```

### Akamai Property Manager Match Rules

**Rule 1: Press Releases List**
```
IF Path matches "/news/press-releases/"
OR Path matches "/news/press-releases/index.html"
THEN
  Set Origin: Hugo S3
  Set Cache TTL: 300 seconds
```

**Rule 2: Press Release Articles (Pattern)**
```
IF Path matches regex "^/news/press-releases/sb03[3-5][0-9]/$"
THEN
  Set Origin: Hugo S3
  Set Cache TTL: 3600 seconds
```

**Rule 3: Hugo Pagination Pages**
```
IF Path matches regex "^/news/press-releases/page/[0-9]+/$"
THEN
  Set Origin: Hugo S3
  Set Cache TTL: 300 seconds
```

**Rule 4: Hugo Static Assets**
```
IF Path matches "/css/treasury.css"
OR Path matches "/css/uswds.min.css"
OR Path matches "/js/treasury.js"
OR Path matches "/js/uswds.min.js"
OR Path starts with "/images/treasury-seal"
THEN
  Set Origin: Hugo S3
  Set Cache TTL: 86400 seconds
```

**Default Rule: Everything Else → Drupal**
```
ELSE
  Set Origin: Drupal (existing default)
```

---

## Query String Handling

### Pagination Parameter

The Hugo site expects pagination via query string for URL compatibility with Drupal:

| URL | Behavior |
|-----|----------|
| `/news/press-releases/` | Page 1 |
| `/news/press-releases/?page=1` | Page 2 (Hugo handles internally) |
| `/news/press-releases/?page=2` | Beyond Hugo pages → falls through to Drupal |

**Important:** The `?page=` query parameter must be forwarded to the origin. Hugo's JavaScript handles the redirect logic.

Akamai Configuration:
```
Cache Key Query Parameters: Include "page"
Forward Query String to Origin: Yes
```

---

## Error Handling

### 404 Behavior

Hugo's `404.html` contains JavaScript that redirects users to the same path on Drupal:

```javascript
// Hugo 404.html behavior
window.location.replace("https://home.treasury.gov" + currentPath);
```

**Akamai should NOT intercept Hugo's 404 response.** Let the Hugo origin return its custom 404 page.

If you prefer Akamai-level fallback:

```
IF Origin Response Code = 404
AND Origin = Hugo S3
THEN
  Redirect 302 to: https://home.treasury.gov{path}
```

---

## Cache Configuration

### Recommended TTLs

| Content Type | TTL | Reasoning |
|--------------|-----|-----------|
| HTML pages | 5 minutes (300s) | Content updates |
| CSS/JS | 24 hours (86400s) | Versioned assets |
| Images | 24 hours (86400s) | Rarely change |

### Cache Key Settings

```
Cache Key Hostname: Origin hostname
Cache Key Query String: Include "page" parameter
Cache Key Path: Include full path
```

### Purge Strategy

When Hugo content is updated:

```bash
# Purge press releases section
akamai purge invalidate --urls \
  "https://home.treasury.gov/news/press-releases/" \
  "https://home.treasury.gov/news/press-releases/page/*"

# Purge specific article
akamai purge invalidate --urls \
  "https://home.treasury.gov/news/press-releases/sb0357/"

# Purge static assets (after CSS/JS changes)
akamai purge invalidate --urls \
  "https://home.treasury.gov/css/treasury.css" \
  "https://home.treasury.gov/js/treasury.js"
```

---

## Complete URL Inventory

### Hugo-Served URLs (Route to S3)

```
# List pages
https://home.treasury.gov/news/press-releases/
https://home.treasury.gov/news/press-releases/page/2/

# Individual articles (20 total)
https://home.treasury.gov/news/press-releases/sb0337/
https://home.treasury.gov/news/press-releases/sb0338/
https://home.treasury.gov/news/press-releases/sb0339/
https://home.treasury.gov/news/press-releases/sb0340/
https://home.treasury.gov/news/press-releases/sb0341/
https://home.treasury.gov/news/press-releases/sb0342/
https://home.treasury.gov/news/press-releases/sb0343/
https://home.treasury.gov/news/press-releases/sb0344/
https://home.treasury.gov/news/press-releases/sb0345/
https://home.treasury.gov/news/press-releases/sb0346/
https://home.treasury.gov/news/press-releases/sb0347/
https://home.treasury.gov/news/press-releases/sb0348/
https://home.treasury.gov/news/press-releases/sb0349/
https://home.treasury.gov/news/press-releases/sb0350/
https://home.treasury.gov/news/press-releases/sb0351/
https://home.treasury.gov/news/press-releases/sb0352/
https://home.treasury.gov/news/press-releases/sb0353/
https://home.treasury.gov/news/press-releases/sb0354/
https://home.treasury.gov/news/press-releases/sb0355/
https://home.treasury.gov/news/press-releases/sb0356/
https://home.treasury.gov/news/press-releases/sb0357/

# Static assets
https://home.treasury.gov/css/treasury.css
https://home.treasury.gov/css/uswds.min.css
https://home.treasury.gov/js/treasury.js
https://home.treasury.gov/js/uswds.min.js
https://home.treasury.gov/images/treasury-seal.svg
```

### Drupal-Served URLs (Default Origin)

Everything else, including:
- Homepage: `https://home.treasury.gov/`
- About section: `https://home.treasury.gov/about/*`
- Policy section: `https://home.treasury.gov/policy-issues/*`
- Other news: `https://home.treasury.gov/news/testimonies/*`
- Data section: `https://home.treasury.gov/data/*`
- Services: `https://home.treasury.gov/services/*`

---

## Testing Checklist

### Pre-Deployment

- [ ] Hugo S3 bucket is publicly accessible
- [ ] S3 static website hosting enabled with `index.html` as default
- [ ] Hugo build deployed to S3 (`hugo --minify && aws s3 sync public/ s3://bucket/`)
- [ ] Akamai origin pointing to correct S3 endpoint

### Post-Deployment Validation

| Test | Expected Result |
|------|-----------------|
| `curl -I https://home.treasury.gov/news/press-releases/` | 200, served from Hugo |
| `curl -I https://home.treasury.gov/news/press-releases/sb0357/` | 200, served from Hugo |
| `curl -I https://home.treasury.gov/` | 200, served from Drupal |
| `curl -I https://home.treasury.gov/about/` | 200, served from Drupal |
| `curl -I https://home.treasury.gov/news/testimonies/` | 200, served from Drupal |
| `curl -I https://home.treasury.gov/news/press-releases/nonexistent/` | 404 from Hugo, redirects to Drupal |

### Browser Tests

1. Visit `/news/press-releases/` → Should display Hugo page with Treasury styling
2. Click article link → Should load Hugo article page
3. Click "Home" in header → Should go to Drupal homepage
4. Click pagination "next" on page 2 → Should go to Drupal's `?page=2`
5. Click any mega menu link → Should go to Drupal site
6. Inspect network tab → CSS/JS should load from Hugo origin

---

## Rollback Procedure

To revert to Drupal-only:

1. Remove Hugo path match rules from Akamai Property Manager
2. Save and activate property version
3. Purge cache for affected paths

```bash
akamai purge invalidate --urls \
  "https://home.treasury.gov/news/press-releases/*"
```

---

## Contact

For questions about this integration:

- **Hugo Site Issues:** [Developer Contact]
- **Akamai Configuration:** [CDN Team Contact]
- **Content Updates:** [Content Team Contact]

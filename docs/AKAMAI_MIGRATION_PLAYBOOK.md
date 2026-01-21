# Akamai Migration Playbook

**Treasury Hugo Site Migration to Akamai CDN**

| Document Info | |
|---------------|---|
| Version | 1.0 |
| Created | January 21, 2026 |
| Status | Ready for Execution |
| Site | home.treasury.gov |
| Migration Type | CloudFront → Akamai (via S3 Origin) |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Pre-Migration Checklist](#3-pre-migration-checklist)
4. [Phase 1: Akamai Configuration](#4-phase-1-akamai-configuration)
5. [Phase 2: Origin Setup & Validation](#5-phase-2-origin-setup--validation)
6. [Phase 3: Path-Based Routing (Hybrid Mode)](#6-phase-3-path-based-routing-hybrid-mode)
7. [Phase 4: Full Cutover](#7-phase-4-full-cutover)
8. [Phase 5: Post-Migration Validation](#8-phase-5-post-migration-validation)
9. [Rollback Procedures](#9-rollback-procedures)
10. [Monitoring & Alerting](#10-monitoring--alerting)
11. [Runbooks](#11-runbooks)
12. [Appendices](#12-appendices)

---

## 1. Executive Summary

### Migration Scope

| Component | Current State | Target State |
|-----------|--------------|--------------|
| **CDN** | AWS CloudFront | Akamai |
| **Origin** | S3 (`treasury-hugo-prod`) | S3 (same bucket) |
| **Legacy CMS** | Drupal (existing) | Drupal (unchanged) |
| **DNS** | Route53 → CloudFront | Route53 → Akamai |
| **SSL/TLS** | ACM Certificate | Akamai Edge Certificate |
| **WAF** | AWS WAF | Akamai Kona/App & API Protector |

### Content Inventory

| Content Type | URLs | Source |
|--------------|------|--------|
| News articles (press releases, statements, testimonies) | 16,564 | Hugo/S3 |
| About section | ~40 pages | Hugo/S3 |
| Policy Issues | ~63 pages | Hugo/S3 |
| Services | ~14 pages | Hugo/S3 |
| Static assets (PDFs, documents) | 15,380 | S3 |
| Dynamic applications (Data Center, TARP) | ~2,500 | Drupal (fallback) |
| **Total Hugo-served** | **~16,700 pages** | S3 |

### Success Criteria

- [ ] Zero downtime during migration
- [ ] All 16,700+ pages accessible via Akamai
- [ ] Response times equal or better than CloudFront (<500ms TTFB)
- [ ] All security headers intact (CSP, HSTS, X-Frame-Options)
- [ ] Cache hit ratio >90% within 24 hours
- [ ] No SEO impact (no broken links, proper redirects)

---

## 2. Architecture Overview

### Current Architecture (CloudFront)

```
                    ┌─────────────────┐
                    │   Route53 DNS   │
                    │ home.treasury.gov│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   CloudFront    │
                    │ (WAF + Headers) │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼────────┐           ┌────────▼────────┐
     │   S3 Bucket     │           │     Drupal      │
     │  (Hugo Site)    │           │   (Legacy CMS)  │
     └─────────────────┘           └─────────────────┘
```

### Target Architecture (Akamai)

```
                    ┌─────────────────┐
                    │   Route53 DNS   │
                    │ home.treasury.gov│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     Akamai      │
                    │   Edge Network  │
                    │  (Kona WAF +    │
                    │   Path Rules)   │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         │ Hugo Paths        │ Drupal Paths      │
         │                   │                   │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│   S3 Bucket     │ │   CloudFront    │ │     Drupal      │
│  (Hugo Site)    │ │   (Optional)    │ │   (Legacy CMS)  │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Path Routing Summary

| Path Pattern | Origin | Cache TTL |
|--------------|--------|-----------|
| `/`, `/index.html` | S3 (Hugo) | 5 min |
| `/news/*` | S3 (Hugo) | 5 min |
| `/about/*` | S3 (Hugo) | 15 min |
| `/policy-issues/*` | S3 (Hugo) | 15 min |
| `/services/*` | S3 (Hugo) | 15 min |
| `/data/*` | S3 (Hugo) | 15 min |
| `/css/*`, `/js/*` | S3 (Hugo) | 1 year (immutable) |
| `/images/*`, `/fonts/*` | S3 (Hugo) | 1 year |
| `/system/files/*` | S3 (Hugo) | 30 days |
| `/resource-center/data-chart-center/*` | Drupal | Pass-through |
| Everything else | Drupal | Drupal default |

---

## 3. Pre-Migration Checklist

### 3.1 Technical Prerequisites

#### Akamai Account & Access

- [ ] Akamai Control Center access confirmed
- [ ] Property Manager access for `home.treasury.gov` property
- [ ] EdgeGrid API credentials configured
- [ ] Akamai CLI installed and authenticated:
  ```bash
  akamai --version
  akamai auth
  ```

#### AWS Access

- [ ] AWS CLI configured with appropriate permissions
- [ ] S3 bucket accessible: `aws s3 ls s3://treasury-hugo-prod/`
- [ ] SSM parameters readable: `aws ssm get-parameter --name /treasury-home/prod/S3_BUCKET_NAME`

#### Network & DNS

- [ ] Current DNS TTL lowered to 300 seconds (done 48 hours before cutover)
- [ ] Route53 access confirmed
- [ ] Current CNAME/A records documented

### 3.2 Content Validation

Run pre-migration content audit:

```bash
# Build site and verify all pages render
hugo --minify --gc

# Count pages
find public -name "*.html" | wc -l
# Expected: ~16,700

# Verify critical pages exist
for page in "" "news/press-releases/" "about/" "policy-issues/"; do
  curl -sI "https://home.treasury.gov/$page" | head -1
done
```

### 3.3 Security Review

- [ ] CSP policy documented (see `terraform/main.tf` line 288-289)
- [ ] HSTS configuration ready
- [ ] TLS 1.2+ only
- [ ] Security headers tested:

```bash
curl -sI https://home.treasury.gov/ | grep -E "^(Strict-Transport|X-Frame|X-Content|Content-Security)"
```

Expected:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
```

### 3.4 Stakeholder Sign-Off

| Stakeholder | Role | Sign-Off |
|-------------|------|----------|
| Platform Team | Infrastructure owner | [ ] |
| Security Team | Security review | [ ] |
| Content Team | Content freeze acknowledgment | [ ] |
| CDN Team | Akamai configuration | [ ] |
| NOC/Operations | Monitoring setup | [ ] |

### 3.5 Communication Plan

| Timing | Action | Audience |
|--------|--------|----------|
| T-7 days | Migration announcement | All stakeholders |
| T-24 hours | Content freeze begins | Content team |
| T-2 hours | Final go/no-go | Platform + CDN teams |
| T-0 | Migration starts | NOC notified |
| T+1 hour | Initial validation complete | All stakeholders |
| T+24 hours | Migration complete announcement | All stakeholders |

---

## 4. Phase 1: Akamai Configuration

### 4.1 Property Setup

Create or configure the Akamai property for `home.treasury.gov`:

**Property Settings:**

| Setting | Value |
|---------|-------|
| Property Name | `home.treasury.gov` |
| Product | Ion Standard or Premium |
| Edge Hostname | `home.treasury.gov.edgekey.net` |
| CP Code | (assigned by Akamai) |
| Contract ID | (your contract) |

### 4.2 Origin Configuration

#### Hugo Origin (S3)

```json
{
  "name": "Hugo_S3_Origin",
  "originType": "CUSTOM",
  "hostname": "treasury-hugo-prod.s3.us-east-1.amazonaws.com",
  "httpPort": 80,
  "httpsPort": 443,
  "originSni": true,
  "verificationMode": "CUSTOM",
  "originCertificate": "",
  "ports": "443",
  "forwardHostHeader": "ORIGIN_HOSTNAME",
  "cacheKeyHostname": "ORIGIN_HOSTNAME",
  "compress": true,
  "enableTrueClientIp": true
}
```

#### Drupal Origin (Existing)

```json
{
  "name": "Drupal_Legacy_Origin",
  "originType": "CUSTOM",
  "hostname": "drupal.treasury.gov",
  "httpPort": 80,
  "httpsPort": 443,
  "originSni": true,
  "forwardHostHeader": "REQUEST_HOST_HEADER"
}
```

### 4.3 Path-Based Routing Rules

Import the caching rules from `deploy/akamai-caching-rules.json`:

#### Rule 1: Hugo Homepage

```
Match:
  Path = "/" OR "/index.html"
Behaviors:
  Origin: Hugo_S3_Origin
  Caching: MAX_AGE 5 minutes
  Gzip: ALWAYS
```

#### Rule 2: News Section (Hugo)

```
Match:
  Path matches "/news/*"
  Content-Type = "text/html"
Behaviors:
  Origin: Hugo_S3_Origin
  Caching: MAX_AGE 5 minutes
  Gzip: ALWAYS
```

#### Rule 3: Static Content Sections (Hugo)

```
Match:
  Path matches one of:
    - "/about/*"
    - "/policy-issues/*"
    - "/services/*"
    - "/data/*"
    - "/resource-center/*"
Behaviors:
  Origin: Hugo_S3_Origin
  Caching: MAX_AGE 15 minutes
  Gzip: ALWAYS
```

#### Rule 4: Fingerprinted Assets (Immutable)

```
Match:
  Path matches "/css/*.*.css" OR "/js/*.*.js"
Behaviors:
  Origin: Hugo_S3_Origin
  Caching: MAX_AGE 365 days
  Cache-Control header: "public, max-age=31536000, immutable"
  Gzip: ALWAYS
  Brotli: ALWAYS
```

#### Rule 5: Images

```
Match:
  Path matches "/images/*" OR file extension in [jpg, jpeg, png, gif, svg, webp, ico]
Behaviors:
  Origin: Hugo_S3_Origin
  Caching: MAX_AGE 365 days
  Prefresh: 90%
```

#### Rule 6: Fonts (with CORS)

```
Match:
  Path matches "/fonts/*" OR file extension in [woff, woff2, ttf, eot]
Behaviors:
  Origin: Hugo_S3_Origin
  Caching: MAX_AGE 365 days
  Add Header: Access-Control-Allow-Origin: *
```

#### Rule 7: Documents (PDFs)

```
Match:
  Path matches "/system/files/*"
  File extension in [pdf, doc, docx, xls, xlsx, ppt, pptx]
Behaviors:
  Origin: Hugo_S3_Origin
  Caching: MAX_AGE 30 days
  Prefresh: 90%
```

#### Rule 8: Service Worker (No Cache)

```
Match:
  Path = "/sw.js"
Behaviors:
  Origin: Hugo_S3_Origin
  Caching: NO_STORE
```

#### Default Rule: Drupal Fallback

```
Match:
  Everything else
Behaviors:
  Origin: Drupal_Legacy_Origin
  Caching: Honor origin headers
```

### 4.4 Security Headers (Response Headers)

Configure via Akamai's "Modify Outgoing Response Header" behavior:

| Header | Value |
|--------|-------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'` |

### 4.5 Compression Settings

```
Enable Brotli: Yes
Enable Gzip: Yes (fallback)
Compress content types:
  - text/html
  - text/css
  - text/javascript
  - application/javascript
  - application/json
  - image/svg+xml
```

### 4.6 TLS Configuration

| Setting | Value |
|---------|-------|
| Minimum TLS Version | TLS 1.2 |
| Preferred Ciphers | ECDHE, AES-GCM |
| HSTS | Enabled |
| OCSP Stapling | Enabled |

---

## 5. Phase 2: Origin Setup & Validation

### 5.1 S3 Bucket Preparation

Ensure the S3 bucket is accessible from Akamai:

```bash
# Verify bucket policy allows Akamai access
aws s3api get-bucket-policy --bucket treasury-hugo-prod

# Test direct S3 access (from Akamai origin perspective)
curl -I "https://treasury-hugo-prod.s3.us-east-1.amazonaws.com/index.html"
```

**Required S3 Bucket Policy for Akamai:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAkamaiAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::treasury-hugo-prod/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": [
            "23.0.0.0/12",
            "104.64.0.0/10"
          ]
        }
      }
    }
  ]
}
```

> **Note:** Get current Akamai IP ranges from Akamai support or use S3 static website endpoint.

**Alternative: Use S3 Website Endpoint:**

```
Origin hostname: treasury-hugo-prod.s3-website-us-east-1.amazonaws.com
Protocol: HTTP only (S3 website doesn't support HTTPS directly)
Akamai: Upgrade to HTTPS at edge
```

### 5.2 Origin Shield (Optional but Recommended)

Configure Akamai Origin Shield to reduce origin load:

| Setting | Value |
|---------|-------|
| Shield Location | US East (Virginia) |
| Shield Hostname | (Akamai assigned) |

Benefits:
- Consolidates origin requests through shield POPs
- Reduces S3 costs
- Improves cache efficiency

### 5.3 Staging Validation

Before production cutover, validate on Akamai staging network:

```bash
# Resolve staging network hostname
dig +short home.treasury.gov.edgesuite-staging.net

# Test via staging
curl -H "Host: home.treasury.gov" \
     -I "https://home.treasury.gov.edgesuite-staging.net/"

# Verify Hugo content is served
curl -H "Host: home.treasury.gov" \
     -s "https://home.treasury.gov.edgesuite-staging.net/news/press-releases/" \
     | grep -o "<title>.*</title>"
```

### 5.4 Functional Testing on Staging

Run the test suite against Akamai staging:

```bash
# Set environment variable for staging host
export TEST_HOST="https://home.treasury.gov.edgesuite-staging.net"

# Run Playwright tests
npx playwright test

# Or run specific critical path tests
npx playwright test 1-visual-layout.spec.ts 2-navigation.spec.ts 7-accessibility-axe.spec.ts
```

**Manual Verification Checklist:**

| Test | Expected Result | Staging Pass |
|------|-----------------|--------------|
| Homepage loads | 200 OK, Hugo content | [ ] |
| `/news/press-releases/` | 200 OK, article list | [ ] |
| `/news/press-releases/sb0357/` | 200 OK, article content | [ ] |
| `/css/treasury.*.css` | 200 OK, Cache-Control: immutable | [ ] |
| `/about/general-information/` | 200 OK, Hugo content | [ ] |
| 404 page | Custom 404.html from Hugo | [ ] |
| CSP header present | Content-Security-Policy header | [ ] |
| HSTS header present | Strict-Transport-Security header | [ ] |
| Gzip/Brotli compression | Content-Encoding: br or gzip | [ ] |

---

## 6. Phase 3: Path-Based Routing (Hybrid Mode)

### 6.1 Hybrid Deployment Strategy

For zero-downtime migration, run in hybrid mode first:

```
Week 1-2: Akamai staging validation
Week 3:   Akamai production (shadow traffic / canary)
Week 4:   DNS cutover to Akamai
Week 5:   Decommission CloudFront
```

### 6.2 Shadow Traffic Testing

Route a percentage of traffic through Akamai while keeping CloudFront as primary:

**Option A: DNS Weighted Routing**

```
home.treasury.gov
├── 90% → CloudFront (current)
└── 10% → Akamai (new)
```

Route53 configuration:
```bash
# Add weighted CNAME for Akamai
aws route53 change-resource-record-sets --hosted-zone-id ZXXXXX \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "home.treasury.gov",
        "Type": "CNAME",
        "SetIdentifier": "akamai-canary",
        "Weight": 10,
        "TTL": 300,
        "ResourceRecords": [{"Value": "home.treasury.gov.edgekey.net"}]
      }
    }]
  }'
```

**Option B: Akamai Site Failover**

Use Akamai SiteShield with CloudFront as failover origin.

### 6.3 Gradual Traffic Shift

| Day | Akamai % | CloudFront % | Notes |
|-----|----------|--------------|-------|
| 1 | 10% | 90% | Initial canary |
| 2 | 10% | 90% | Monitor for errors |
| 3 | 25% | 75% | Increase if stable |
| 5 | 50% | 50% | Halfway point |
| 7 | 75% | 25% | Majority on Akamai |
| 10 | 100% | 0% | Full cutover |

### 6.4 Path Migration Order

Migrate path patterns incrementally to reduce risk:

| Phase | Paths | Risk Level |
|-------|-------|------------|
| 3a | Static assets (`/css/*`, `/js/*`, `/fonts/*`, `/images/*`) | Low |
| 3b | Individual articles (`/news/press-releases/sb*/`) | Low |
| 3c | List pages (`/news/press-releases/`, `/news/press-releases/page/*`) | Medium |
| 3d | Section indexes (`/about/`, `/policy-issues/`, `/services/`) | Medium |
| 3e | Homepage (`/`) | High |

---

## 7. Phase 4: Full Cutover

### 7.1 Pre-Cutover Checklist

**T-24 Hours:**
- [ ] Content freeze in effect
- [ ] Final Hugo build deployed to S3: `./deploy/s3-sync.sh prod`
- [ ] S3 bucket versioning confirmed (rollback capability)
- [ ] Akamai staging tests all passing
- [ ] NOC alerted to upcoming change
- [ ] Support team briefed on potential user reports

**T-2 Hours:**
- [ ] Go/No-Go decision made
- [ ] DNS TTL confirmed at 300 seconds
- [ ] Monitoring dashboards open
- [ ] Runbook accessible to all operators
- [ ] Communication channels open (Slack/Teams)

**T-0 (Cutover Time):**
- [ ] Recommended: Tuesday-Thursday, 6:00 AM - 8:00 AM ET
- [ ] Avoid: Fridays, Mondays, end-of-month, holidays

### 7.2 DNS Cutover Procedure

```bash
# Document current DNS state
dig +short home.treasury.gov

# Update Route53 to point to Akamai
aws route53 change-resource-record-sets \
  --hosted-zone-id ZXXXXX \
  --change-batch file://dns-cutover.json

# dns-cutover.json:
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "home.treasury.gov",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [
          {"Value": "home.treasury.gov.edgekey.net"}
        ]
      }
    }
  ]
}

# Verify propagation
watch -n 10 "dig +short home.treasury.gov"
```

### 7.3 Cutover Validation Script

```bash
#!/bin/bash
# validate-cutover.sh

DOMAIN="home.treasury.gov"
EXPECTED_EDGE="akamai"

echo "=== Post-Cutover Validation ==="
echo "Time: $(date)"
echo ""

# 1. DNS Resolution
echo "1. DNS Check:"
dig +short $DOMAIN
echo ""

# 2. Edge Network Check
echo "2. Edge Network:"
curl -sI "https://$DOMAIN/" | grep -E "^(Server|X-Akamai|X-Cache)"
echo ""

# 3. Critical Pages
echo "3. Critical Page Checks:"
for path in "" "news/press-releases/" "about/" "policy-issues/" "services/"; do
  status=$(curl -sI "https://$DOMAIN/$path" | head -1 | awk '{print $2}')
  echo "   /$path -> $status"
done
echo ""

# 4. Security Headers
echo "4. Security Headers:"
curl -sI "https://$DOMAIN/" | grep -E "^(Strict-Transport|X-Frame|Content-Security)"
echo ""

# 5. Cache Headers
echo "5. Cache Headers (CSS):"
curl -sI "https://$DOMAIN/css/treasury.css" | grep -E "^(Cache-Control|Age|X-Cache)"
echo ""

# 6. Response Times
echo "6. Response Times:"
for i in 1 2 3; do
  time curl -so /dev/null "https://$DOMAIN/news/press-releases/"
done

echo ""
echo "=== Validation Complete ==="
```

### 7.4 Smoke Tests Post-Cutover

```bash
# Run full Playwright test suite
cd /Users/ludwitt/home.treasury.gov
npx playwright test --reporter=html

# Open report
npx playwright show-report
```

---

## 8. Phase 5: Post-Migration Validation

### 8.1 Functional Validation Matrix

| Category | Test | Status |
|----------|------|--------|
| **Pages** | | |
| | Homepage loads | [ ] |
| | Press releases list | [ ] |
| | Individual article | [ ] |
| | About section | [ ] |
| | Policy Issues | [ ] |
| | Services | [ ] |
| | 404 page works | [ ] |
| **Navigation** | | |
| | Mega menu opens | [ ] |
| | Mobile nav works | [ ] |
| | Breadcrumbs correct | [ ] |
| | Pagination works | [ ] |
| **Search** | | |
| | Main search redirects to USA.gov | [ ] |
| | Keyword filter works | [ ] |
| | Date filter works | [ ] |
| **Assets** | | |
| | CSS loads | [ ] |
| | JavaScript executes | [ ] |
| | Images display | [ ] |
| | Fonts render | [ ] |
| | PDFs accessible | [ ] |
| **Security** | | |
| | HTTPS enforced | [ ] |
| | CSP header present | [ ] |
| | HSTS header present | [ ] |
| | X-Frame-Options: DENY | [ ] |
| **Performance** | | |
| | TTFB < 500ms | [ ] |
| | LCP < 2.5s | [ ] |
| | CLS < 0.1 | [ ] |

### 8.2 SEO Validation

```bash
# Check robots.txt
curl -s "https://home.treasury.gov/robots.txt"

# Check sitemap
curl -sI "https://home.treasury.gov/sitemap.xml"

# Verify canonical URLs
curl -s "https://home.treasury.gov/news/press-releases/" | grep -o '<link rel="canonical"[^>]*>'

# Check Google Search Console for crawl errors (manual)
```

### 8.3 Cache Warm-Up

Populate Akamai cache for critical pages:

```bash
#!/bin/bash
# cache-warmup.sh

DOMAIN="home.treasury.gov"

# Critical pages to warm
PAGES=(
  "/"
  "/news/press-releases/"
  "/news/press-releases/page/2/"
  "/about/"
  "/about/general-information/"
  "/policy-issues/"
  "/services/"
)

# Recent press releases (get from sitemap)
RECENT=$(curl -s "https://$DOMAIN/news/press-releases/index.xml" | \
         grep -oP '(?<=<link>)[^<]+' | head -20)

echo "Warming cache for $DOMAIN"
echo "=========================="

for page in "${PAGES[@]}"; do
  echo -n "Warming: $page ... "
  curl -so /dev/null "https://$DOMAIN$page"
  echo "done"
done

for url in $RECENT; do
  echo -n "Warming: $url ... "
  curl -so /dev/null "$url"
  echo "done"
done

echo ""
echo "Cache warm-up complete"
```

### 8.4 Performance Baseline

Capture post-migration metrics:

```bash
# Using Lighthouse CLI
npm install -g lighthouse
lighthouse https://home.treasury.gov --output=json --output-path=./metrics-post-migration.json

# Key metrics to capture:
# - First Contentful Paint
# - Largest Contentful Paint  
# - Time to Interactive
# - Cumulative Layout Shift
# - Speed Index
```

### 8.5 24-Hour Monitoring Period

After cutover, monitor closely for 24 hours:

| Time | Check | Owner |
|------|-------|-------|
| T+15min | Quick smoke test | On-call engineer |
| T+1hr | Full validation script | Platform team |
| T+4hr | Cache hit ratio check | CDN team |
| T+8hr | Error rate review | NOC |
| T+24hr | Complete metrics review | Platform lead |

---

## 9. Rollback Procedures

### 9.1 Rollback Triggers

Initiate rollback if any of the following occur:

| Trigger | Threshold | Decision |
|---------|-----------|----------|
| 5xx error rate | >1% for 15 minutes | Rollback |
| TTFB | >2s for 30 minutes | Investigate, possible rollback |
| Homepage down | >5 minutes | Immediate rollback |
| Security headers missing | Any duration | Immediate rollback |
| Cache hit ratio | <50% after 4 hours | Investigate |

### 9.2 Rollback Procedure

**Step 1: Revert DNS (2 minutes)**

```bash
# Point back to CloudFront
aws route53 change-resource-record-sets \
  --hosted-zone-id ZXXXXX \
  --change-batch file://dns-rollback.json

# dns-rollback.json:
{
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "home.treasury.gov",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2FDTNDATAQYW2",
          "DNSName": "dXXXXXXXXXXXXX.cloudfront.net",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
```

**Step 2: Verify CloudFront is serving (5 minutes)**

```bash
# Wait for DNS propagation
sleep 60

# Verify requests hitting CloudFront
curl -sI https://home.treasury.gov/ | grep -E "^(Server|X-Cache|Via)"
# Should show: Via: ... CloudFront
```

**Step 3: Purge Akamai cache if needed**

```bash
./deploy/akamai-purge.sh
```

**Step 4: Post-mortem**

- Document what went wrong
- Timeline of events
- Root cause analysis
- Prevention measures

### 9.3 Rollback Communication

| Audience | Message | Channel |
|----------|---------|---------|
| NOC | Rollback initiated, CloudFront active | Slack/PagerDuty |
| Stakeholders | Brief service disruption, resolved | Email |
| CDN Team | Akamai config review needed | Meeting |

---

## 10. Monitoring & Alerting

### 10.1 Akamai Monitoring Setup

**DataStream 2 Configuration:**

| Field | Value |
|-------|-------|
| Dataset | Access logs |
| Delivery | S3 bucket or Splunk |
| Format | JSON |
| Frequency | Real-time |

**Key Metrics to Monitor:**

| Metric | Alert Threshold | Description |
|--------|-----------------|-------------|
| `edgeHits` | - | Total requests to edge |
| `originHits` | >10% of edge | Too many origin fetches |
| `cacheMissRatio` | >20% | Poor cache efficiency |
| `status5xx` | >1% | Server errors |
| `status4xx` | >5% | Client errors |
| `ttfbMs` | >500ms p95 | Slow responses |

### 10.2 Synthetic Monitoring

Set up synthetic checks in your monitoring platform:

```yaml
# Example: Datadog Synthetic Test
name: "Treasury Hugo - Homepage"
type: "browser"
url: "https://home.treasury.gov/"
frequency: 60  # seconds
locations:
  - aws:us-east-1
  - aws:us-west-2
  - aws:eu-west-1
assertions:
  - type: statusCode
    operator: is
    target: 200
  - type: responseTime
    operator: lessThan
    target: 3000
  - type: body
    operator: contains
    target: "U.S. Department of the Treasury"
```

### 10.3 Log Analysis Queries

**High Error Rate Detection:**
```sql
-- Splunk/CloudWatch Logs Insights
SELECT status, COUNT(*) as count
FROM akamai_access_logs
WHERE timestamp > NOW() - INTERVAL 15 MINUTE
GROUP BY status
ORDER BY count DESC
```

**Slow Response Investigation:**
```sql
SELECT url, AVG(ttfbMs) as avg_ttfb, COUNT(*) as requests
FROM akamai_access_logs
WHERE timestamp > NOW() - INTERVAL 1 HOUR
  AND ttfbMs > 500
GROUP BY url
ORDER BY avg_ttfb DESC
LIMIT 20
```

### 10.4 Alerting Rules

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| High 5xx Rate | >1% for 5 min | Critical | Page on-call |
| Homepage Down | 3 consecutive failures | Critical | Page on-call |
| Cache Miss Spike | >30% for 15 min | Warning | Investigate |
| Origin Overload | Origin requests >1000/min | Warning | Check origin health |
| SSL Certificate Expiry | <30 days | Warning | Renew certificate |

---

## 11. Runbooks

### 11.1 Daily Operations

**Deploy Content Update:**

```bash
# 1. Pull latest content changes
cd /Users/ludwitt/home.treasury.gov
git pull origin staging

# 2. Build and deploy to S3
./deploy/s3-sync.sh prod --yes

# 3. Purge Akamai cache
./deploy/akamai-purge.sh

# 4. Verify deployment
curl -sI https://home.treasury.gov/news/press-releases/ | head -5
```

**Emergency Content Update:**

```bash
# Direct push with immediate cache purge
./deploy/s3-sync.sh prod --yes && ./deploy/akamai-purge.sh
```

### 11.2 Cache Purge Operations

**Purge Entire Site:**

```bash
./deploy/akamai-purge.sh
```

**Purge Specific Paths:**

```bash
# Single page
akamai purge invalidate --urls "https://home.treasury.gov/news/press-releases/sb0357/"

# Section
akamai purge invalidate --urls \
  "https://home.treasury.gov/news/press-releases/" \
  "https://home.treasury.gov/news/press-releases/page/*"

# Static assets (after CSS/JS changes)
akamai purge invalidate --urls \
  "https://home.treasury.gov/css/*" \
  "https://home.treasury.gov/js/*"
```

### 11.3 Troubleshooting Guide

**Problem: Page returning 404**

```bash
# Check if page exists in S3
aws s3 ls s3://treasury-hugo-prod/news/press-releases/sb0357/index.html

# Check Akamai routing
curl -sI -H "Pragma: akamai-x-check-cacheable" \
  "https://home.treasury.gov/news/press-releases/sb0357/" | \
  grep -E "^(HTTP|X-Check|X-Cache)"
```

**Problem: Stale content being served**

```bash
# Check cache age
curl -sI https://home.treasury.gov/news/press-releases/ | grep -E "^(Age|X-Cache|Cache-Control)"

# Purge and refresh
akamai purge invalidate --urls "https://home.treasury.gov/news/press-releases/"
curl -sI https://home.treasury.gov/news/press-releases/
```

**Problem: CSP violations in browser**

```bash
# Check CSP header is present
curl -sI https://home.treasury.gov/ | grep "Content-Security-Policy"

# If missing, check Akamai response header configuration
# Verify "Modify Outgoing Response Header" behavior is active
```

**Problem: Slow response times**

```bash
# Test from multiple locations
for region in us-east-1 us-west-2 eu-west-1; do
  echo "Testing from $region:"
  time curl -so /dev/null "https://home.treasury.gov/"
done

# Check if hitting origin
curl -sI -H "Pragma: akamai-x-get-cache-key" \
  "https://home.treasury.gov/" | grep -E "^(X-Cache|X-True-Cache)"
```

### 11.4 Incident Response

**Severity 1: Site Down**

1. Confirm outage: `curl -sI https://home.treasury.gov/`
2. Check Akamai status: [status.akamai.com](https://status.akamai.com)
3. Check S3 origin: `curl -sI https://treasury-hugo-prod.s3.us-east-1.amazonaws.com/index.html`
4. If Akamai issue: Escalate to Akamai support
5. If persistent: Initiate rollback to CloudFront

**Severity 2: Partial Degradation**

1. Identify affected paths
2. Check origin health for those paths
3. Purge cache for affected URLs
4. Monitor for recovery

---

## 12. Appendices

### Appendix A: Complete URL Inventory

Hugo-served paths (route to S3):

```
/                                    # Homepage
/news/*                              # All news content
/news/press-releases/                # Press releases list
/news/press-releases/page/*/         # Paginated lists
/news/press-releases/*/              # Individual articles
/news/statements-remarks/            # Statements
/news/testimonies/                   # Testimonies
/news/readouts/                      # Readouts
/news/featured-stories/              # Featured stories
/about/                              # About section
/about/general-information/*         # General info pages
/about/offices/*                     # Office pages
/about/history/*                     # History pages
/policy-issues/                      # Policy section
/policy-issues/*/                    # Individual policy pages
/services/                           # Services section
/data/                               # Data section
/css/*                               # Stylesheets
/js/*                                # JavaScript
/images/*                            # Images
/fonts/*                             # Fonts
/system/files/*                      # Uploaded documents
/404.html                            # Error page
/sitemap.xml                         # XML sitemap
/index.xml                           # RSS feed
```

Drupal-served paths (route to legacy origin):

```
/resource-center/data-chart-center/interest-rates/TextView*  # Interest rate data
/data/troubled-assets-relief-program/*                       # TARP data
/resource-center/data-chart-center/tic/*                     # TIC data
/*                                                           # Everything else
```

### Appendix B: Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| Platform Lead | [name] | Primary |
| Akamai TAM | [name] | Akamai issues |
| AWS Support | Enterprise Support | S3/origin issues |
| NOC | noc@treasury.gov | 24/7 monitoring |
| Content Team | [name] | Content issues |

### Appendix C: Related Documentation

| Document | Location |
|----------|----------|
| Akamai Integration Guide | `docs/AKAMAI_INTEGRATION.md` |
| Migration Analysis | `docs/MIGRATION_ANALYSIS.md` |
| Dynamic Apps Migration | `docs/DYNAMIC_APPLICATIONS_MIGRATION.md` |
| Deployment Scripts | `deploy/README.md` |
| Testing Instructions | `docs/TESTING_INSTRUCTIONS.md` |
| Post-Migration Roadmap | `docs/POST_MIGRATION_ROADMAP.md` |

### Appendix D: Akamai Property Manager Export

Reference configuration is stored in `deploy/akamai-caching-rules.json`.

### Appendix E: Terraform Resources to Update

After successful Akamai migration, update Terraform to reflect new architecture:

```hcl
# Remove or comment out:
# - aws_cloudfront_distribution.site
# - aws_cloudfront_origin_access_control.site
# - aws_wafv2_web_acl.cloudfront

# Add:
# - Documentation of Akamai property
# - Updated S3 bucket policy for Akamai IPs

# Update:
# - aws_route53_record.site_a (point to Akamai)
```

### Appendix F: Validation Script

Full validation script for post-migration:

```bash
#!/bin/bash
# full-validation.sh

set -e

DOMAIN="home.treasury.gov"
ERRORS=0

log() { echo "[$(date '+%H:%M:%S')] $1"; }
pass() { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; ((ERRORS++)); }

log "Starting full validation for $DOMAIN"
echo "============================================"

# 1. DNS Resolution
log "1. DNS Check"
IP=$(dig +short $DOMAIN | head -1)
if [[ -n "$IP" ]]; then
  pass "DNS resolves to $IP"
else
  fail "DNS resolution failed"
fi

# 2. HTTPS Connection
log "2. HTTPS Check"
STATUS=$(curl -sI "https://$DOMAIN/" | head -1 | awk '{print $2}')
if [[ "$STATUS" == "200" ]]; then
  pass "Homepage returns 200"
else
  fail "Homepage returns $STATUS"
fi

# 3. Security Headers
log "3. Security Headers"
HEADERS=$(curl -sI "https://$DOMAIN/")
for header in "Strict-Transport-Security" "X-Frame-Options" "Content-Security-Policy"; do
  if echo "$HEADERS" | grep -qi "^$header:"; then
    pass "$header present"
  else
    fail "$header missing"
  fi
done

# 4. Critical Pages
log "4. Critical Pages"
PAGES=("news/press-releases/" "about/" "policy-issues/" "services/")
for page in "${PAGES[@]}"; do
  STATUS=$(curl -sI "https://$DOMAIN/$page" | head -1 | awk '{print $2}')
  if [[ "$STATUS" == "200" ]]; then
    pass "/$page returns 200"
  else
    fail "/$page returns $STATUS"
  fi
done

# 5. Static Assets
log "5. Static Assets"
CSS=$(curl -sI "https://$DOMAIN/css/treasury.css" | head -1 | awk '{print $2}')
JS=$(curl -sI "https://$DOMAIN/js/treasury.js" | head -1 | awk '{print $2}')
if [[ "$CSS" == "200" ]] && [[ "$JS" == "200" ]]; then
  pass "CSS and JS accessible"
else
  fail "Static assets not accessible (CSS: $CSS, JS: $JS)"
fi

# 6. Cache Headers
log "6. Cache Headers"
CACHE=$(curl -sI "https://$DOMAIN/css/treasury.css" | grep -i "cache-control" | head -1)
if echo "$CACHE" | grep -qi "max-age"; then
  pass "Cache-Control header present: $CACHE"
else
  fail "Cache-Control header missing or invalid"
fi

# 7. Compression
log "7. Compression"
ENCODING=$(curl -sI -H "Accept-Encoding: gzip, br" "https://$DOMAIN/" | grep -i "content-encoding" | head -1)
if echo "$ENCODING" | grep -qiE "(gzip|br)"; then
  pass "Compression enabled: $ENCODING"
else
  fail "Compression not detected"
fi

# 8. Response Time
log "8. Response Time"
TIME=$(curl -so /dev/null -w "%{time_total}" "https://$DOMAIN/")
if (( $(echo "$TIME < 2.0" | bc -l) )); then
  pass "Response time acceptable: ${TIME}s"
else
  fail "Response time too slow: ${TIME}s"
fi

echo ""
echo "============================================"
if [[ $ERRORS -eq 0 ]]; then
  echo "✅ All validations passed!"
  exit 0
else
  echo "❌ $ERRORS validation(s) failed"
  exit 1
fi
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-21 | Initial playbook creation |

---

*End of Akamai Migration Playbook*

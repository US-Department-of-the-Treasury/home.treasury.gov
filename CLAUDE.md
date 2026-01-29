# Treasury Home Hugo Site

Hugo-based static site for home.treasury.gov deployed to AWS S3/CloudFront.

## Git Workflow

**NEVER force push to git.** Always create new commits to fix issues.

**Default branch is `staging`** (not `main` or `master`)

This project uses a **staging → master** branching strategy with automatic deployments:

| Branch | Purpose | Auto-Deploy Target |
|--------|---------|-------------------|
| `staging` | Default branch. All feature branches merge here. | Staging environment |
| `master` | Production branch. Merge from staging to deploy. | Production environment |

### Feature Development (feature → staging)

1. Create feature branch from `staging`: `git checkout -b feature/my-feature staging`
2. Make changes and commit
3. Create PR targeting `staging`:
```bash
gh pr create --base staging --head feature/my-feature
```

### Production Deploy (staging → master)

After changes are verified on staging:
1. Create PR from `staging` to `master`
2. Merge triggers auto-deploy to production via GitHub Actions

## Deployment

```bash
./deploy/s3-sync.sh staging   # Deploy to staging
./deploy/s3-sync.sh prod      # Deploy to production (requires confirmation)
```

The deploy script automatically:
- Builds Hugo site with `--minify`
- Syncs to S3 with appropriate cache headers
- Invalidates CloudFront cache (fetches config from SSM)

## Pre-Deployment Checklist

**REQUIRED before every deploy:**

### CSP Compliance Check

This site enforces strict Content Security Policy. Before deploying, verify:

1. **No inline scripts** - All JavaScript must be in external `.js` files
   - Check: `grep -r "<script>" themes/ --include="*.html" | grep -v "src="`
   - Should return NO results (except Hugo template tags)

2. **No inline event handlers** - No `onclick`, `onload`, etc. in HTML
   - Check: `grep -rE "on(click|load|change|submit|error)=" themes/ --include="*.html"`
   - Should return NO results

3. **External scripts only from 'self'** - No CDN scripts allowed
   - All JS must be in `themes/treasury/assets/js/` and loaded via Hugo pipes

### CSP Policy Reference

```
script-src 'self'              # Only external scripts from same origin
style-src 'self' 'unsafe-inline'  # Styles can be inline (for Hugo)
img-src 'self' data: https:    # Images from self, data URIs, or HTTPS
```

### Quick CSP Test After Deploy

Open browser DevTools Console and check for CSP violations:
- Navigate to https://stg2.treasury.gov/news/search/
- Look for "Content Security Policy" errors
- All pages with JavaScript should be tested

## Hugo Assets

JavaScript files go in `themes/treasury/assets/js/` and are loaded via Hugo pipes:

```go
{{ $js := resources.Get "js/myfile.js" | minify | fingerprint }}
<script src="{{ $js.RelPermalink }}"></script>
```

This ensures:
- Files are minified in production
- Cache-busting via content hash
- CSP compliance (external script from 'self')

## SSM Parameters

Configuration is stored in AWS SSM Parameter Store:

| Parameter | Description |
|-----------|-------------|
| `/treasury-home/staging/S3_BUCKET_NAME` | S3 bucket for staging |
| `/treasury-home/staging/CLOUDFRONT_DISTRIBUTION_ID` | CloudFront distribution |
| `/treasury-home/staging/CLOUDFRONT_DOMAIN` | CloudFront domain |
| `/treasury-home/staging/SITE_URL` | Public site URL |

## Lenis Smooth Scrolling (Variant Pages)

The variant pages in `static/variants/` use Lenis for smooth scrolling. **Critical constraints:**

1. **Never use CSS `scroll-behavior: smooth` with Lenis** - they conflict and cause scroll jank
2. **Avoid SVG `feTurbulence` filters** - extremely expensive, kills scroll performance
3. **GPU-accelerate fixed overlays** - add `will-change: transform; transform: translateZ(0);`

Required Lenis CSS (always include):
```css
html.lenis, html.lenis body { height: auto; }
.lenis.lenis-smooth { scroll-behavior: auto !important; }
```

See `docs/solutions/performance-issues/lenis-smooth-scroll-performance.md` for full details.

## Infrastructure

Terraform configuration in `terraform/` manages:
- S3 bucket with static website hosting
- CloudFront distribution with custom domain
- ACM certificate for HTTPS
- Route53 DNS records
- robots.txt for non-production environments

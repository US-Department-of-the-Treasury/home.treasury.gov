# Deployment Scripts

Scripts for deploying the Hugo site to AWS S3 and managing Akamai cache.

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with credentials
- [Akamai CLI](https://developer.akamai.com/cli) with purge module
- Proper IAM permissions for S3 bucket access

## Configuration

1. Copy the example config:
   ```bash
   cp config.env.example config.env
   ```

2. Edit `config.env` with your values:
   ```bash
   S3_BUCKET_STAGING="your-staging-bucket"
   S3_BUCKET_PROD="your-production-bucket"
   CLOUDFRONT_DISTRIBUTION_ID="your-cf-id"
   ```

3. The `config.env` file is gitignored for security.

## Scripts

### `s3-sync.sh`

Builds the Hugo site and syncs to S3.

```bash
# Deploy to staging
./deploy/s3-sync.sh staging

# Deploy to production
./deploy/s3-sync.sh prod
```

**What it does:**
1. Runs `hugo --minify` to build the site
2. Syncs `public/` to the specified S3 bucket
3. Sets appropriate cache headers
4. Reports sync results

### `akamai-purge.sh`

Purges Akamai CDN cache after deployment.

```bash
# Purge all cached content
./deploy/akamai-purge.sh

# Purge specific paths
./deploy/akamai-purge.sh /news/press-releases/
```

**When to use:**
- After deploying content updates
- After CSS/JS changes
- When cached content needs immediate refresh

### `pre-migration-checklist.sh`

Validates environment readiness before Akamai migration.

```bash
./deploy/pre-migration-checklist.sh
```

**Checks performed:**
- Hugo, AWS CLI, Akamai CLI installed
- AWS credentials and S3 access
- Akamai authentication
- Hugo build success
- CSP compliance (no inline scripts)
- DNS TTL configuration

### `validate-akamai.sh`

Validates Hugo site is correctly served through Akamai.

```bash
# Validate production
./deploy/validate-akamai.sh

# Validate staging network
./deploy/validate-akamai.sh staging

# Quick smoke test
./deploy/validate-akamai.sh --quick
```

**Validates:**
- DNS and connectivity
- Akamai edge headers
- Security headers (CSP, HSTS, X-Frame-Options)
- Critical pages (200 OK)
- Static assets and caching
- Compression
- 404 handling
- Response times

## Branching and Deployment Workflow

This project uses a **staging → master** branching strategy with automatic deployments:

| Branch | Purpose | Auto-Deploy Target |
|--------|---------|-------------------|
| `staging` | Default branch. All feature branches merge here. | Staging environment |
| `master` | Production branch. Merge from staging to deploy. | Production environment |

### How It Works

1. **Feature Development**: Create feature branches from `staging`, merge PRs back to `staging`
2. **Staging Deploy**: Push to `staging` triggers GitHub Actions → deploys to staging
3. **Production Deploy**: Merge `staging` into `master` → GitHub Actions deploys to production

### Setting Up Default Branch (One-Time Setup)

To set `staging` as the default branch in GitHub:

1. Go to your repository on GitHub
2. Click **Settings** → **General**
3. Under "Default branch", click the edit button (pencil icon)
4. Select `staging` from the dropdown
5. Click **Update**
6. Confirm the change

This ensures new PRs target `staging` by default.

### GitHub Secrets (Required for Auto-Deploy)

The GitHub Actions workflow requires these secrets to deploy to AWS:

| Secret Name | Description |
|-------------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key with S3 and CloudFront permissions |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key |

**To add secrets in GitHub:**

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Enter the secret name (e.g., `AWS_ACCESS_KEY_ID`)
5. Enter the secret value
6. Click **Add secret**
7. Repeat for `AWS_SECRET_ACCESS_KEY`

**IAM Permissions Required:**

The IAM user/role needs these permissions:
- `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on the S3 bucket
- `cloudfront:CreateInvalidation` on the CloudFront distribution
- `ssm:GetParameter` for reading SSM parameters

### Manual Deployment (Local)

```bash
# 1. Build and deploy to staging
./deploy/s3-sync.sh staging

# 2. Verify at staging URL

# 3. Deploy to production (requires confirmation)
./deploy/s3-sync.sh prod

# 4. Purge Akamai cache
./deploy/akamai-purge.sh
```

### Emergency Content Update

```bash
# Direct to production with cache purge (skip confirmation with --yes)
./deploy/s3-sync.sh prod --yes && ./deploy/akamai-purge.sh
```

## S3 Bucket Configuration

The S3 bucket should be configured for static website hosting:

- **Index document**: `index.html`
- **Error document**: `404.html`
- **Block public access**: Disabled (for static hosting)
- **Bucket policy**: Allow public read

Example bucket policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

## Akamai Migration

### Pre-Migration Checklist

Before migrating to Akamai, run the pre-flight checklist:

```bash
./deploy/pre-migration-checklist.sh
```

This validates:
- Local environment (Hugo, AWS CLI, Akamai CLI)
- AWS access and S3 bucket configuration
- Akamai CLI authentication
- Hugo build success
- Current site status
- Security configuration (CSP compliance)
- DNS TTL settings

### Validate Akamai Configuration

After configuring Akamai, validate the setup:

```bash
# Validate staging network
./deploy/validate-akamai.sh staging

# Validate production (after cutover)
./deploy/validate-akamai.sh

# Quick smoke test only
./deploy/validate-akamai.sh --quick
```

### Full Migration Playbook

See [docs/AKAMAI_MIGRATION_PLAYBOOK.md](../docs/AKAMAI_MIGRATION_PLAYBOOK.md) for the complete migration guide including:

- Architecture overview
- Phase-by-phase migration steps
- Path-based routing configuration
- Rollback procedures
- Monitoring and alerting
- Runbooks for common operations

### Akamai Configuration Reference

See [docs/AKAMAI_INTEGRATION.md](../docs/AKAMAI_INTEGRATION.md) for detailed Akamai configuration including:

- Origin configuration
- Path-based routing rules
- Cache TTL settings
- Complete URL inventory

## Troubleshooting

### S3 Sync Fails

1. Check AWS CLI credentials: `aws sts get-caller-identity`
2. Verify bucket exists: `aws s3 ls s3://bucket-name`
3. Check IAM permissions for `s3:PutObject`, `s3:DeleteObject`

### Akamai Purge Fails

1. Verify Akamai CLI auth: `akamai auth`
2. Check purge module: `akamai install purge`
3. Confirm property/CP code access

### Content Not Updating

1. Clear browser cache
2. Check Akamai cache status
3. Verify S3 sync completed successfully
4. Run cache purge: `./deploy/akamai-purge.sh`

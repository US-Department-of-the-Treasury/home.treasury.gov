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

## Deployment Workflow

### Standard Deployment

```bash
# 1. Build and deploy to staging
./deploy/s3-sync.sh staging

# 2. Verify at staging URL

# 3. Deploy to production
./deploy/s3-sync.sh prod

# 4. Purge Akamai cache
./deploy/akamai-purge.sh
```

### Emergency Content Update

```bash
# Direct to production with cache purge
./deploy/s3-sync.sh prod && ./deploy/akamai-purge.sh
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

## Akamai Integration

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

# Treasury Hugo Site - Common Tasks
# Run `make help` to see available commands

.PHONY: help serve build clean test deploy-staging deploy-prod lint

# Default target
help:
	@echo "Treasury Hugo Site - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make serve          Start development server (port 1313)"
	@echo "  make build          Build site for production"
	@echo "  make clean          Remove build artifacts"
	@echo ""
	@echo "Testing:"
	@echo "  make test           Run link validation"
	@echo "  make test-508       Run Section 508 accessibility tests"
	@echo "  make lint           Check for issues"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-staging Deploy to staging environment"
	@echo "  make deploy-prod    Deploy to production"
	@echo ""
	@echo "Content:"
	@echo "  make scrape         Scrape latest press releases"
	@echo "  make new-pr         Create new press release (interactive)"
	@echo ""

# Development server
serve:
	hugo server -D --port 1313 --navigateToChanged

# Production build
build:
	hugo --minify

# Clean build artifacts
clean:
	rm -rf public/
	rm -rf resources/_gen/
	rm -f hugo_stats.json

# Run link validation
test:
	python scripts/test_links.py

# Run Section 508 accessibility tests
test-508:
	@echo "Running Section 508 / WCAG 2.1 AA compliance tests..."
	@echo "Testing: http://localhost:1313/news/press-releases/"
	@command -v pa11y-ci >/dev/null 2>&1 || { echo "Installing pa11y-ci..."; npm install -g pa11y-ci; }
	pa11y-ci || echo "If npm fails, run: sudo chown -R \$$(whoami) ~/.npm"

# Run accessibility test on single URL
test-508-url:
	@read -p "Enter URL to test: " url; \
	npx pa11y "$$url" --standard WCAG2AA

# Check for common issues
lint:
	@echo "Checking Hugo build..."
	@hugo --quiet && echo "✓ Hugo build OK" || echo "✗ Hugo build failed"
	@echo ""
	@echo "Checking JSON syntax..."
	@python -m json.tool data/navigation.json > /dev/null && echo "✓ navigation.json OK" || echo "✗ navigation.json invalid"
	@echo ""
	@echo "Checking for draft content..."
	@grep -r "draft: true" content/ 2>/dev/null && echo "⚠ Draft content found" || echo "✓ No drafts"

# Deploy to staging
deploy-staging:
	./deploy/s3-sync.sh staging

# Deploy to production
deploy-prod:
	./deploy/s3-sync.sh prod
	./deploy/akamai-purge.sh

# Scrape latest press releases
scrape:
	python scripts/scrape_press_releases.py --pages 5

# Create new press release (uses Hugo archetype)
new-pr:
	@read -p "Enter slug (e.g., 2026-01-15-sb0358): " slug; \
	hugo new news/press-releases/$$slug.md
	@echo "Created new press release. Edit content/news/press-releases/$$slug.md"

# Install Python dependencies
setup:
	pip install -r requirements.txt

# Watch for changes and rebuild
watch:
	hugo server -D --port 1313 --disableFastRender

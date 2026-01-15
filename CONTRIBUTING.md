# Contributing to Treasury Hugo Site

Thank you for your interest in contributing to the U.S. Department of the Treasury Hugo site.

## Getting Started

### Prerequisites

- [Hugo Extended](https://gohugo.io/installation/) v0.120.0+
- [Python 3.10+](https://www.python.org/) (for scripts)
- [Git](https://git-scm.com/)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd home.treasury.gov

# Install Python dependencies (for scraping/testing scripts)
pip install -r requirements.txt

# Start development server
hugo server -D --port 1313
```

## Project Structure

```
├── archetypes/      # Content templates
├── content/         # Markdown content
├── data/            # JSON data files
├── deploy/          # Deployment scripts
├── docs/            # Documentation
├── scripts/         # Python utilities
└── themes/treasury/ # Hugo theme
```

## Making Changes

### Content Changes

1. Press releases go in `content/news/press-releases/`
2. Use the archetype: `hugo new news/press-releases/YYYY-MM-DD-title.md`
3. Follow existing front matter conventions

### Theme Changes

1. Templates are in `themes/treasury/layouts/`
2. CSS is in `themes/treasury/static/css/treasury.css`
3. JavaScript is in `themes/treasury/static/js/treasury.js`

### Navigation Changes

1. Edit `data/navigation.json`
2. Run `python scripts/test_links.py` to validate URLs

## Code Style

### Hugo Templates

- Use 2-space indentation
- Comment complex logic with `{{/* comment */}}`
- Prefer partials for reusable components

### CSS

- Follow existing naming conventions
- Use CSS variables for colors/spacing
- Mobile-first responsive design

### Python Scripts

- Follow PEP 8 style guide
- Include docstrings for functions
- Add type hints where practical

## Testing

### Before Submitting

1. **Build test**: `hugo --minify` should complete without errors
2. **Link validation**: `python scripts/test_links.py`
3. **Visual check**: Review changes in browser at `http://localhost:1313`

### Common Issues

- Check for Hugo template syntax errors in terminal output
- Validate JSON syntax in data files
- Ensure all links use correct paths

## Submitting Changes

### Pull Request Process

1. Create a feature branch: `git checkout -b feature/description`
2. Make your changes with clear commit messages
3. Test locally
4. Push and create a pull request
5. Describe what changed and why

### Commit Messages

Use clear, descriptive commit messages:

```
Add: New press release template
Fix: Broken navigation link to OFAC
Update: Footer social media icons
Remove: Deprecated scraping script
```

## Questions?

- Review existing documentation in `docs/`
- Check `scripts/README.md` for utility scripts
- See `docs/AKAMAI_INTEGRATION.md` for deployment details

## License

This project is in the public domain. See [LICENSE](LICENSE) for details.

All contributions will be released under the same terms.

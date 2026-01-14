# Treasury Hugo Theme

A Hugo theme for the U.S. Department of the Treasury, built on the [U.S. Web Design System (USWDS)](https://designsystem.digital.gov/).

## Features

- USWDS 3.x compliant design
- Mega menu navigation with dropdowns
- Mobile-responsive layout
- Government banner ("An official website...")
- Alert banner for announcements
- Breadcrumb navigation
- Press release templates
- Dark footer matching Treasury.gov

## Structure

```
treasury/
├── layouts/
│   ├── _default/
│   │   ├── baseof.html    # Base template
│   │   ├── list.html      # Default list page
│   │   └── single.html    # Default single page
│   ├── news/
│   │   ├── list.html      # News listing with pagination
│   │   └── single.html    # Individual article
│   ├── partials/
│   │   ├── alert-banner.html
│   │   ├── breadcrumbs.html
│   │   ├── footer.html
│   │   ├── header.html
│   │   ├── news-search-sidebar.html
│   │   ├── news-sidebar.html
│   │   └── usa-banner.html
│   ├── 404.html           # Error page (redirects to live site)
│   └── index.html         # Homepage (redirects to live site)
├── static/
│   ├── css/
│   │   └── treasury.css   # All site styles
│   ├── js/
│   │   └── treasury.js    # Navigation, search, slider
│   └── images/
│       ├── treasury-seal.svg
│       ├── secretary-bessent.jpg
│       └── ...
└── theme.toml             # Theme metadata
```

## Partials

### `usa-banner.html`
Official government website banner with expandable "Here's how you know" section.

### `alert-banner.html`
Dismissible alert banner. Configure message in `hugo.toml`:
```toml
[params]
  alert_message = "Your alert message here"
```

### `header.html`
Main header with Treasury branding and mega menu navigation. Navigation structure defined in `data/navigation.json`.

### `footer.html`
Dark footer with:
- Treasury seal
- 5 columns: Bureaus, IG Sites, Shared Services, Resources, Gov Sites
- Utility bar with legal links
- Social media icons

### `breadcrumbs.html`
Automatic breadcrumb navigation based on page hierarchy.

### `news-sidebar.html`
Left sidebar for news pages with category links.

### `news-search-sidebar.html`
Right sidebar with keyword search and subscribe button.

## Configuration

Required in `hugo.toml`:

```toml
theme = "treasury"

[params]
  description = "Site description"
  agency = "U.S. Department of the Treasury"
  logo = "/images/treasury-seal.svg"
  alert_message = ""  # Leave empty to hide
  twitter = "USTreasury"
  facebook = "USTreasuryDept"
  address = "1500 Pennsylvania Avenue, NW, Washington, D.C. 20220"
  phone = "(202) 622-2000"
```

## Navigation

Navigation is data-driven from `data/navigation.json`:

```json
{
  "main_nav": [
    {
      "title": "About Treasury",
      "url": "/about/",
      "columns": [
        {
          "heading": "General Information",
          "links": [
            {"title": "Role of the Treasury", "url": "/about/general-information/role-of-the-treasury"}
          ]
        }
      ]
    }
  ]
}
```

## Customization

### Colors

CSS variables in `static/css/treasury.css`:

```css
:root {
  --treasury-navy: #112e51;
  --treasury-navy-dark: #0c2340;
  --treasury-gold: #ffbe2e;
  --treasury-green: #4d8055;
}
```

### Typography

Uses system fonts with USWDS styling conventions.

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

Public Domain - U.S. Government Work

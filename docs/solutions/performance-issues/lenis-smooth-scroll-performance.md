---
title: Lenis Smooth Scroll Performance Issues
category: performance-issues
tags: [lenis, scroll, css, performance, animation, gpu]
problem_type: scroll_jank
components: [variants, css, javascript]
date_created: 2026-01-25
root_cause: css_conflict_and_expensive_effects
severity: high
---

# Lenis Smooth Scroll Performance Issues

## Problem Symptom

Scrolling on variant pages exhibited "insane lag" - choppy, stuttering scroll behavior despite having Lenis smooth scroll library loaded. Some variants had no smooth scrolling at all.

## Investigation Steps

1. **Initial check**: Used Playwright MCP to navigate to variant pages and test scroll behavior
2. **Library presence**: Verified which variants had Lenis loaded vs missing
   - WITH Lenis: variants 1, 2, 4, 6, 7, 9, 10
   - WITHOUT Lenis: variants 3, 5, 8
3. **Performance profiling**: Identified CSS conflicts and expensive visual effects causing repaints

## Root Cause Analysis

### Issue 1: CSS `scroll-behavior: smooth` Conflicts with Lenis

**ALL 10 variants** had this CSS rule:

```css
html {
  scroll-behavior: smooth;
}
```

When both native CSS smooth scrolling AND Lenis are active, they fight each other, causing jank. Lenis takes control of scrolling via JavaScript, but the browser's native smooth scroll tries to interpolate simultaneously.

### Issue 2: Expensive SVG Filter Effects

Variants 1, 2, 5, and 7 had this extremely expensive visual effect:

```css
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background: url("data:image/svg+xml,...<feTurbulence>...");
  pointer-events: none;
  z-index: 9999;
}
```

The `<feTurbulence>` SVG filter is computationally expensive and runs on every frame during scroll, causing severe performance degradation. Fixed-position elements with complex filters trigger full-page repaints.

### Issue 3: Missing Lenis Library

Variants 3, 5, and 8 never loaded the Lenis library at all - they only had the CSS that conflicted with it.

## Working Solution

### Fix 1: Remove Native Smooth Scroll CSS

Remove or override `scroll-behavior: smooth`:

```css
/* REMOVE this from html/body styles */
/* scroll-behavior: smooth; */

/* OR add Lenis overrides */
html.lenis, html.lenis body {
  height: auto;
}
.lenis.lenis-smooth {
  scroll-behavior: auto !important;
}
.lenis.lenis-smooth [data-lenis-prevent] {
  overscroll-behavior: contain;
}
.lenis.lenis-stopped {
  overflow: hidden;
}
```

### Fix 2: Remove Expensive SVG Filters

Replace feTurbulence-based noise effects with lighter alternatives:

```css
/* REMOVE expensive SVG turbulence filter */
/* body::before with feTurbulence SVG background */

/* If visual effect is needed, use CSS-only alternative */
body::after {
  content: '';
  position: fixed;
  inset: 0;
  background:
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0, 0, 0, 0.03) 2px,
      rgba(0, 0, 0, 0.03) 4px
    );
  pointer-events: none;
  z-index: 9999;
  /* GPU acceleration for fixed overlays */
  will-change: transform;
  transform: translateZ(0);
}
```

### Fix 3: Add GPU Acceleration to Fixed Overlays

Any fixed-position overlay elements should have GPU acceleration:

```css
.fixed-overlay {
  will-change: transform;
  transform: translateZ(0);
}
```

### Fix 4: Add Lenis Script Where Missing

```html
<!-- Before </body> -->
<script src="https://unpkg.com/lenis@1.1.18/dist/lenis.min.js"></script>
<script>
  const lenis = new Lenis({
    lerp: 0.1,
    smoothWheel: true,
  });
  function raf(time) {
    lenis.raf(time);
    requestAnimationFrame(raf);
  }
  requestAnimationFrame(raf);
</script>
```

## Prevention Strategies

### Pre-Implementation Checklist for Smooth Scrolling

1. **Never use both** CSS `scroll-behavior: smooth` AND a JS smooth scroll library together
2. **Audit visual effects** before implementation - SVG filters with `feTurbulence`, `feDisplacementMap`, `feConvolveMatrix` are extremely expensive
3. **GPU-accelerate fixed elements** - Any `position: fixed` element should have `transform: translateZ(0)` and `will-change: transform`
4. **Test on lower-powered devices** - Effects that work on M3 Mac may destroy performance on older hardware

### Code Review Red Flags

| Pattern | Issue |
|---------|-------|
| `scroll-behavior: smooth` with Lenis | CSS/JS conflict |
| `<feTurbulence>` in any SVG | Expensive filter |
| `position: fixed` without GPU hints | Repaint on scroll |
| Large base64 SVG backgrounds | Memory + decode cost |

### Lenis CSS Template

Always include this CSS when using Lenis:

```css
/* Lenis smooth scroll - REQUIRED CSS */
html.lenis, html.lenis body {
  height: auto;
}
.lenis.lenis-smooth {
  scroll-behavior: auto !important;
}
.lenis.lenis-smooth [data-lenis-prevent] {
  overscroll-behavior: contain;
}
.lenis.lenis-stopped {
  overflow: hidden;
}
```

## Files Changed

- `static/variants/1/index.html` - Removed feTurbulence, added GPU acceleration, Lenis CSS
- `static/variants/2/index.html` - Removed feTurbulence, Lenis CSS
- `static/variants/3/index.html` - Added Lenis CSS + script
- `static/variants/4/index.html` - Lenis CSS fix
- `static/variants/5/index.html` - Removed feTurbulence, added Lenis CSS + script
- `static/variants/6/index.html` - Lenis CSS
- `static/variants/7/index.html` - Removed feTurbulence, Lenis CSS
- `static/variants/8/index.html` - Added Lenis CSS + script
- `static/variants/9/index.html` - Lenis CSS
- `static/variants/10/index.html` - Lenis CSS

## Cross-References

- [Lenis Documentation](https://github.com/darkroomengineering/lenis)
- MDN: [scroll-behavior](https://developer.mozilla.org/en-US/docs/Web/CSS/scroll-behavior)
- MDN: [feTurbulence](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/feTurbulence)
- Web.dev: [Avoid large, complex layouts and layout thrashing](https://web.dev/avoid-large-complex-layouts-and-layout-thrashing/)

## Summary

When using Lenis (or any JS smooth scroll library):
1. Remove CSS `scroll-behavior: smooth`
2. Avoid expensive SVG filters on fixed elements
3. GPU-accelerate fixed overlays
4. Always include Lenis CSS overrides

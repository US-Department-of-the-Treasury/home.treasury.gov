# Automated Testing Instructions

Instructions for testing the Treasury Hugo site using a browser automation tool.

## Test Environment

- **Local URL**: `http://localhost:1313`
- **Live Treasury Site**: `https://home.treasury.gov`

Start the local server before testing:
```bash
cd /Users/ludwitt/home.treasury.gov
hugo server -D --port 1313
```

---

## Test Scenarios

### 1. Press Releases List Page

**URL**: `http://localhost:1313/news/press-releases/`

**Verify:**
- [ ] Page loads with Treasury header and navigation
- [ ] Government banner ("An official website of the United States government") is visible
- [ ] Alert banner is displayed (if configured)
- [ ] Left sidebar shows "NEWS" with category links
- [ ] Main content shows list of press releases with dates
- [ ] Right sidebar shows "KEYWORD SEARCH" form
- [ ] Pagination shows page numbers (1, 2) and arrows
- [ ] Footer displays with dark navy background and Treasury seal

---

### 2. Individual Press Release Page

**URL**: `http://localhost:1313/news/press-releases/sb0357/`

**Verify:**
- [ ] Breadcrumb shows: HOME > NEWS > PRESS RELEASES
- [ ] Article title is displayed
- [ ] Article content is rendered
- [ ] Left sidebar with news categories is visible
- [ ] Right sidebar with search form is visible

---

### 3. Navigation - Home Links

**Test**: Click the Treasury logo in the header

**Expected**: Redirects to `https://home.treasury.gov/`

**Test**: Click the Treasury logo in the sticky nav (scroll down first)

**Expected**: Redirects to `https://home.treasury.gov/`

**Test**: Click "HOME" in the breadcrumb

**Expected**: Redirects to `https://home.treasury.gov/`

---

### 4. Navigation - Mega Menu

**Test**: Click "About Treasury" in the main nav

**Expected**: Mega menu dropdown opens with columns of links

**Test**: Click any link in the mega menu (e.g., "Role of the Treasury")

**Expected**: Redirects to `https://home.treasury.gov/about/general-information/role-of-the-treasury`

**Test**: Click other nav items (Policy Issues, Data, Services, News)

**Expected**: Each opens a mega menu; all links go to `home.treasury.gov`

---

### 5. Search Functionality

#### Main Navigation Search

**Test**: 
1. Click the "SEARCH" button in the navigation
2. Enter "sanctions" in the search field
3. Click "GO"

**Expected**: Redirects to `https://search.usa.gov/search?affiliate=treasury&query=sanctions`

#### Keyword Search Sidebar

**Test**:
1. Go to `http://localhost:1313/news/press-releases/`
2. In the right sidebar, enter "muslim" in the keyword field
3. Click "APPLY"

**Expected**: Redirects to `https://home.treasury.gov/news/press-releases/?title=muslim`

#### Date Range Search

**Test**:
1. Go to `http://localhost:1313/news/press-releases/`
2. Set Start date: 2025-12-01
3. Set End date: 2025-12-31
4. Click "APPLY"

**Expected**: Redirects to `https://home.treasury.gov/news/press-releases/?publication-start-date=2025-12-01&publication-end-date=2025-12-31`

---

### 6. Pagination

**Test**: On the press releases list, click page "2"

**Expected**: Goes to `http://localhost:1313/news/press-releases/?page=1` (Hugo page 2)

**Test**: On page 2, click the right arrow (→)

**Expected**: Redirects to `https://home.treasury.gov/news/press-releases?page=2` (live site continuation)

**Test**: On page 1, click the left arrow (←)

**Expected**: Goes to `https://home.treasury.gov/news/press-releases` (live site page 0)

---

### 7. Footer Links

**Test**: Scroll to footer and verify links

**Bureau links should go to:**
- TTB → `https://www.ttb.gov/`
- BEP → `https://www.bep.gov/`
- IRS → `https://www.irs.gov/`
- U.S. Mint → `https://www.usmint.gov/`

**Social links should go to:**
- X → `https://x.com/USTreasury`
- Facebook → `https://www.facebook.com/USTreasuryDept/`

**Utility links should go to:**
- Privacy Policy → `https://home.treasury.gov/subfooter/privacy-policy`
- Accessibility → `https://home.treasury.gov/subfooter/accessibility`

---

### 8. 404 Redirect

**Test**: Visit a non-existent page: `http://localhost:1313/about/nonexistent-page/`

**Expected**: 
- Briefly shows "Redirecting..." message
- Automatically redirects to `https://home.treasury.gov/about/nonexistent-page/`

---

### 9. Homepage Redirect

**Test**: Visit `http://localhost:1313/`

**Expected**: Immediately redirects to `https://home.treasury.gov/`

---

### 10. Subscribe Button

**Test**: Click "Subscribe to Press Releases" button in right sidebar

**Expected**: Opens `https://public.govdelivery.com/accounts/USTREAS/subscriber/new?topic_id=USTREAS_49` in the same tab

---

### 11. Left Sidebar Navigation

**Test**: On press releases page, click links in left sidebar

**Expected behaviors:**
- "Press Releases" → Stays on current page (active)
- "Statements & Remarks" → Goes to `https://home.treasury.gov/news/press-releases/statements-remarks`
- "Readouts" → Goes to `https://home.treasury.gov/news/press-releases/readouts`
- "Testimonies" → Goes to `https://home.treasury.gov/news/press-releases/testimonies`
- "Featured Stories" → Goes to `https://home.treasury.gov/news/featured-stories`
- "Webcasts" → Goes to `https://home.treasury.gov/news/webcasts`
- "Press Contacts" → Goes to `https://home.treasury.gov/news/contacts-for-members-of-the-media`

---

### 12. Mobile Responsiveness

**Test**: Resize browser to mobile width (~375px)

**Verify:**
- [ ] Navigation collapses to hamburger menu
- [ ] Content stacks vertically
- [ ] Footer columns stack
- [ ] All functionality remains accessible

---

### 13. Link Target Behavior

**Test**: All links should open in the same tab (no `target="_blank"`)

**Verify by clicking:**
- Navigation links
- Footer links
- Social media links
- Subscribe button

**Expected**: All open in the same browser tab

---

## Test Summary Checklist

| Test | Pass/Fail |
|------|-----------|
| Press releases list loads correctly | |
| Individual article page works | |
| Home links redirect to live site | |
| Mega menu links go to live site | |
| Main search goes to USA.gov search | |
| Keyword search goes to live site | |
| Date search goes to live site | |
| Pagination works correctly | |
| Page 2+ continues to live site | |
| Footer links work | |
| 404 redirects to live site | |
| Homepage redirects to live site | |
| Subscribe button works | |
| Left sidebar links work | |
| Mobile layout is functional | |
| All links open in same tab | |

---

## Reporting Issues

If a test fails, document:
1. The URL where the issue occurred
2. The expected behavior
3. The actual behavior
4. Browser console errors (if any)
5. Screenshot of the issue

Report issues in the project repository or contact the development team.

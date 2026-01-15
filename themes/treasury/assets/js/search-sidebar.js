/**
 * News Search Sidebar
 * Client-side search and filtering for Treasury news
 */
(function() {
  'use strict';
  
  // Get filter config from data attribute
  const sidebar = document.getElementById('mobile-search-panel');
  if (!sidebar) return;
  
  const FILTERS = JSON.parse(sidebar.dataset.filters || '{}');
  
  let searchIndex = null;
  let results = [];
  let page = 1;
  const perPage = 15;
  
  // Elements
  const $ = id => document.getElementById(id);
  const keyword = $('keyword-input');
  const startDate = $('start-date');
  const endDate = $('end-date');
  const president = $('president-select');
  const secretary = $('secretary-select');
  const moreToggle = $('more-filters-toggle');
  const morePanel = $('more-filters-panel');
  const activeFilters = $('active-filters');
  const activeTags = $('active-filter-tags');
  const btnSearch = $('btn-search');
  const btnClear = $('btn-clear');
  const resultsDiv = $('search-results');
  const resultsList = $('results-list');
  const resultsCount = $('results-count');
  const pagination = $('results-pagination');
  const btnReset = $('btn-reset');
  const mobileClose = $('mobile-filter-close');
  const mobileToggle = document.getElementById('mobile-filter-toggle');
  const overlay = $('filter-overlay');
  
  // Load search index
  async function loadIndex() {
    if (searchIndex) return;
    const res = await fetch('/index.json');
    searchIndex = await res.json();
  }
  
  // Get current filter state
  function getFilters() {
    return {
      keyword: keyword.value.trim(),
      startDate: startDate.value,
      endDate: endDate.value,
      president: president.value,
      secretary: secretary.value,
      topics: [...document.querySelectorAll('input[name="topic"]:checked')].map(c => c.value),
      offices: [...document.querySelectorAll('input[name="office"]:checked')].map(c => c.value),
      countries: [...document.querySelectorAll('input[name="country"]:checked')].map(c => c.value)
    };
  }
  
  // Check if any filters are active
  function hasFilters() {
    const f = getFilters();
    return f.keyword || f.startDate || f.endDate || f.president || f.secretary || 
           f.topics.length || f.offices.length || f.countries.length;
  }
  
  // Update active filter tags display
  function updateTags() {
    const f = getFilters();
    const tags = [];
    
    if (f.keyword) tags.push({ type: 'keyword', label: `"${f.keyword}"` });
    if (f.startDate || f.endDate) tags.push({ type: 'date', label: `${f.startDate || '...'} to ${f.endDate || '...'}` });
    
    if (f.president) {
      const p = FILTERS.presidents?.find(x => x.id === f.president);
      if (p) tags.push({ type: 'president', label: p.label });
    }
    if (f.secretary) {
      const s = FILTERS.secretaries?.find(x => x.id === f.secretary);
      if (s) tags.push({ type: 'secretary', label: s.label });
    }
    
    f.topics.forEach(t => {
      const x = FILTERS.topics?.find(y => y.id === t);
      if (x) tags.push({ type: 'topic', value: t, label: x.label });
    });
    f.offices.forEach(o => {
      const x = FILTERS.offices?.find(y => y.id === o);
      if (x) tags.push({ type: 'office', value: o, label: x.shortLabel });
    });
    f.countries.forEach(c => {
      const x = FILTERS.countries?.find(y => y.id === c);
      if (x) tags.push({ type: 'country', value: c, label: x.label });
    });
    
    if (tags.length === 0) {
      activeFilters.hidden = true;
      btnClear.hidden = true;
      return;
    }
    
    activeFilters.hidden = false;
    btnClear.hidden = false;
    activeTags.innerHTML = tags.map(t => `
      <span class="filter-tag" data-type="${t.type}" data-value="${t.value || ''}">
        ${t.label}
        <button type="button" aria-label="Remove ${t.label}">×</button>
      </span>
    `).join('');
    
    activeTags.querySelectorAll('button').forEach(btn => {
      btn.onclick = () => {
        const tag = btn.parentElement;
        removeFilter(tag.dataset.type, tag.dataset.value);
      };
    });
  }
  
  // Remove a specific filter
  function removeFilter(type, value) {
    switch(type) {
      case 'keyword': keyword.value = ''; break;
      case 'date': startDate.value = ''; endDate.value = ''; break;
      case 'president': president.value = ''; break;
      case 'secretary': secretary.value = ''; break;
      case 'topic':
        document.querySelector(`input[name="topic"][value="${value}"]`).checked = false;
        break;
      case 'office':
        document.querySelector(`input[name="office"][value="${value}"]`).checked = false;
        break;
      case 'country':
        document.querySelector(`input[name="country"][value="${value}"]`).checked = false;
        break;
    }
    updateTags();
    if (hasFilters()) doSearch();
    else clearResults();
  }
  
  // Clear all filters
  function clearAll() {
    keyword.value = '';
    startDate.value = '';
    endDate.value = '';
    president.value = '';
    secretary.value = '';
    document.querySelectorAll('input[type="checkbox"]').forEach(c => c.checked = false);
    updateTags();
    clearResults();
  }
  
  function clearResults() {
    resultsDiv.hidden = true;
    results = [];
    page = 1;
  }
  
  // Perform search
  async function doSearch() {
    if (!hasFilters()) return;
    
    if (!searchIndex) {
      resultsList.innerHTML = '<div class="no-results">Loading...</div>';
      resultsDiv.hidden = false;
      await loadIndex();
    }
    
    const f = getFilters();
    const kw = f.keyword.toLowerCase().split(/\s+/).filter(w => w);
    
    results = searchIndex.filter(item => {
      // Keyword match
      if (kw.length && !kw.every(w => item.title.toLowerCase().includes(w))) return false;
      // Date range
      if (f.startDate && item.date < f.startDate) return false;
      if (f.endDate && item.date > f.endDate) return false;
      // President filter
      if (f.president && item.president !== f.president) return false;
      // Secretary filter
      if (f.secretary && item.secretary !== f.secretary) return false;
      // Topics filter
      if (f.topics.length && (!item.topics || !f.topics.some(t => item.topics.includes(t)))) return false;
      // Offices filter
      if (f.offices.length && (!item.offices || !f.offices.some(o => item.offices.includes(o)))) return false;
      // Countries filter
      if (f.countries.length && (!item.countries || !f.countries.some(c => item.countries.includes(c)))) return false;
      
      return true;
    });
    
    page = 1;
    renderResults();
  }
  
  // Render results
  function renderResults() {
    const start = (page - 1) * perPage;
    const slice = results.slice(start, start + perPage);
    const totalPages = Math.ceil(results.length / perPage);
    
    resultsCount.textContent = `${results.length} result${results.length !== 1 ? 's' : ''}`;
    
    if (slice.length === 0) {
      resultsList.innerHTML = '<div class="no-results">No results found. Try adjusting your filters.</div>';
    } else {
      resultsList.innerHTML = slice.map(item => `
        <article class="result-item">
          <div class="result-date">${item.dateDisplay}</div>
          <h3 class="result-title"><a href="${item.url}">${escapeHtml(item.title)}</a></h3>
        </article>
      `).join('');
    }
    
    // Pagination
    if (totalPages > 1) {
      let html = '';
      if (page > 1) html += `<button data-page="${page-1}">←</button>`;
      for (let i = Math.max(1, page-2); i <= Math.min(totalPages, page+2); i++) {
        html += `<button data-page="${i}" class="${i === page ? 'current' : ''}">${i}</button>`;
      }
      if (page < totalPages) html += `<button data-page="${page+1}">→</button>`;
      pagination.innerHTML = html;
      pagination.querySelectorAll('button').forEach(b => {
        b.onclick = () => { page = +b.dataset.page; renderResults(); };
      });
    } else {
      pagination.innerHTML = '';
    }
    
    resultsDiv.hidden = false;
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
  
  function scrollToTop() {
    sidebar.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  
  // Event bindings
  moreToggle.onclick = () => {
    const expanded = moreToggle.getAttribute('aria-expanded') === 'true';
    moreToggle.setAttribute('aria-expanded', !expanded);
    morePanel.hidden = expanded;
  };
  
  btnSearch.onclick = () => { updateTags(); doSearch(); };
  btnClear.onclick = () => { clearAll(); scrollToTop(); };
  btnReset.onclick = () => { clearAll(); scrollToTop(); };
  
  keyword.onkeydown = e => { if (e.key === 'Enter') { updateTags(); doSearch(); } };
  
  // Mobile handling
  if (mobileToggle) {
    mobileToggle.onclick = () => {
      sidebar.classList.add('mobile-open');
      overlay.hidden = false;
    };
  }
  
  mobileClose.onclick = () => {
    sidebar.classList.remove('mobile-open');
    overlay.hidden = true;
  };
  
  overlay.onclick = () => {
    sidebar.classList.remove('mobile-open');
    overlay.hidden = true;
  };
  
  // Preload index on focus
  keyword.addEventListener('focus', loadIndex, { once: true });
})();

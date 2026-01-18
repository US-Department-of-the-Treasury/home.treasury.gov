/**
 * News Inline Filters
 * Quick filtering for news section pages
 */
document.addEventListener('DOMContentLoaded', function() {
  console.log('[InlineFilters] Initializing...');
  
  // Get current section from URL
  var currentPath = window.location.pathname;
  var sectionMatch = currentPath.match(/\/news\/([^\/]+)/);
  var currentSection = sectionMatch ? sectionMatch[1] : 'all';
  console.log('[InlineFilters] Current section:', currentSection);
  
  // State
  var searchIndex = null;
  var activeFilters = {
    datePreset: null,
    dateFrom: null,
    dateTo: null,
    keyword: ''
  };
  
  // DOM elements
  var quickFilterBtns = document.querySelectorAll('.quick-filter-btn');
  var dateFromInput = document.getElementById('filter-date-from');
  var dateToInput = document.getElementById('filter-date-to');
  var keywordInput = document.getElementById('filter-keyword');
  var applyBtn = document.getElementById('apply-filters-btn');
  var clearBtn = document.getElementById('clear-filters-btn');
  var resetBtn = document.getElementById('reset-to-paginated');
  var activeFiltersEl = document.getElementById('active-filters');
  var filterTagsEl = document.getElementById('filter-tags');
  var filteredResultsEl = document.getElementById('filtered-results');
  var paginatedContentEl = document.getElementById('paginated-content');
  var resultsListEl = document.getElementById('inline-results-list');
  var resultsCountEl = document.getElementById('inline-results-count');
  var resultsPaginationEl = document.getElementById('inline-results-pagination');
  
  // Exit early if filter elements don't exist
  if (!quickFilterBtns.length || !dateFromInput) {
    console.log('[InlineFilters] Filter elements not found, skipping initialization');
    return;
  }
  
  console.log('[InlineFilters] DOM elements:', {
    paginatedContentEl: !!paginatedContentEl,
    filteredResultsEl: !!filteredResultsEl,
    applyBtn: !!applyBtn
  });
  
  // Load search index
  async function loadSearchIndex() {
    if (searchIndex) return searchIndex;
    try {
      var response = await fetch('/index.json');
      searchIndex = await response.json();
      return searchIndex;
    } catch (error) {
      console.error('Failed to load search index:', error);
      return [];
    }
  }
  
  // Date helpers
  function getDateRange(preset) {
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    switch (preset) {
      case 'today':
        return { from: today, to: today };
      case 'week':
        var weekAgo = new Date(today);
        weekAgo.setDate(weekAgo.getDate() - 7);
        return { from: weekAgo, to: today };
      case 'month':
        var monthAgo = new Date(today);
        monthAgo.setMonth(monthAgo.getMonth() - 1);
        return { from: monthAgo, to: today };
      case 'year':
        var yearAgo = new Date(today);
        yearAgo.setFullYear(yearAgo.getFullYear() - 1);
        return { from: yearAgo, to: today };
      default:
        return null;
    }
  }
  
  function formatDateForInput(date) {
    return date.toISOString().split('T')[0];
  }
  
  function formatDateDisplay(dateStr) {
    var date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }
  
  // Section name mapping (URL path -> display names)
  var sectionMap = {
    'press-releases': ['press releases', 'press-releases'],
    'readouts': ['readouts'],
    'statements-remarks': ['statements & remarks', 'statements-remarks', 'statements remarks'],
    'testimonies': ['testimonies'],
    'featured-stories': ['featured stories', 'featured-stories'],
    'webcasts': ['webcasts']
  };
  
  // Filter the search index
  function filterResults(items) {
    return items.filter(function(item) {
      // Section filter (built-in based on current page)
      if (currentSection !== 'all') {
        var itemSection = (item.section || '').toLowerCase();
        var validSections = sectionMap[currentSection] || [currentSection];
        if (!validSections.some(function(s) {
          return itemSection.includes(s) || s.includes(itemSection);
        })) {
          return false;
        }
      }
      
      // Date filter
      if (activeFilters.dateFrom || activeFilters.dateTo) {
        var itemDate = new Date(item.date);
        if (activeFilters.dateFrom && itemDate < new Date(activeFilters.dateFrom)) return false;
        if (activeFilters.dateTo) {
          var toDate = new Date(activeFilters.dateTo);
          toDate.setHours(23, 59, 59, 999);
          if (itemDate > toDate) return false;
        }
      }
      
      // Keyword filter
      if (activeFilters.keyword) {
        var searchText = (item.title + ' ' + (item.content || '')).toLowerCase();
        var keywords = activeFilters.keyword.toLowerCase().split(/\s+/);
        if (!keywords.every(function(kw) { return searchText.includes(kw); })) return false;
      }
      
      return true;
    });
  }
  
  // Render results
  function renderResults(items, page) {
    page = page || 1;
    var perPage = 10;
    var start = (page - 1) * perPage;
    var end = start + perPage;
    var pageItems = items.slice(start, end);
    var totalPages = Math.ceil(items.length / perPage);
    
    // Update count
    resultsCountEl.textContent = 'Showing ' + pageItems.length + ' of ' + items.length + ' results';
    
    // Render items
    resultsListEl.innerHTML = pageItems.map(function(item) {
      var date = new Date(item.date);
      var dateStr = date.toLocaleDateString('en-US', { 
        year: 'numeric', month: 'long', day: 'numeric',
        hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
      });
      
      return '<article class="news-article-item">' +
        '<div class="article-meta">' +
        '<time datetime="' + item.date + '">' + dateStr + '</time>' +
        (item.section ? '<span class="article-category-divider">|</span><span class="article-category">' + item.section + '</span>' : '') +
        '</div>' +
        '<h2><a href="' + item.url + '">' + item.title + '</a></h2>' +
        '</article>';
    }).join('');
    
    // Render pagination
    if (totalPages > 1) {
      var paginationHtml = '';
      
      // Previous
      if (page > 1) {
        paginationHtml += '<button class="page-arrow" data-page="' + (page - 1) + '">← Prev</button>';
      }
      
      // Page numbers
      var startPage = Math.max(1, page - 2);
      var endPage = Math.min(totalPages, page + 2);
      
      if (startPage > 1) {
        paginationHtml += '<button class="page-number" data-page="1">1</button>';
        if (startPage > 2) paginationHtml += '<span class="page-ellipsis">...</span>';
      }
      
      for (var i = startPage; i <= endPage; i++) {
        var currentClass = i === page ? 'current' : '';
        paginationHtml += '<button class="page-number ' + currentClass + '" data-page="' + i + '">' + i + '</button>';
      }
      
      if (endPage < totalPages) {
        if (endPage < totalPages - 1) paginationHtml += '<span class="page-ellipsis">...</span>';
        paginationHtml += '<button class="page-number" data-page="' + totalPages + '">' + totalPages + '</button>';
      }
      
      // Next
      if (page < totalPages) {
        paginationHtml += '<button class="page-arrow" data-page="' + (page + 1) + '">Next →</button>';
      }
      
      resultsPaginationEl.innerHTML = paginationHtml;
      resultsPaginationEl.style.display = 'flex';
      
      // Add pagination click handlers
      resultsPaginationEl.querySelectorAll('[data-page]').forEach(function(btn) {
        btn.addEventListener('click', function() {
          renderResults(items, parseInt(btn.dataset.page));
          filteredResultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      });
    } else {
      resultsPaginationEl.style.display = 'none';
    }
  }
  
  // Update active filters display
  function updateActiveFiltersDisplay() {
    var tags = [];
    
    if (activeFilters.datePreset) {
      var presetLabels = {
        today: 'Today',
        week: 'This Week',
        month: 'This Month',
        year: 'This Year'
      };
      tags.push({ type: 'preset', label: presetLabels[activeFilters.datePreset] });
    } else if (activeFilters.dateFrom || activeFilters.dateTo) {
      var label = '';
      if (activeFilters.dateFrom && activeFilters.dateTo) {
        label = formatDateDisplay(activeFilters.dateFrom) + ' – ' + formatDateDisplay(activeFilters.dateTo);
      } else if (activeFilters.dateFrom) {
        label = 'From ' + formatDateDisplay(activeFilters.dateFrom);
      } else {
        label = 'Until ' + formatDateDisplay(activeFilters.dateTo);
      }
      tags.push({ type: 'date', label: label });
    }
    
    if (activeFilters.keyword) {
      tags.push({ type: 'keyword', label: '"' + activeFilters.keyword + '"' });
    }
    
    if (tags.length > 0) {
      filterTagsEl.innerHTML = tags.map(function(tag) {
        return '<span class="filter-tag" data-type="' + tag.type + '">' +
          tag.label +
          '<button class="remove-tag" aria-label="Remove filter">×</button>' +
          '</span>';
      }).join('');
      
      // Add remove handlers
      filterTagsEl.querySelectorAll('.remove-tag').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
          var type = e.target.closest('.filter-tag').dataset.type;
          if (type === 'preset') {
            activeFilters.datePreset = null;
            activeFilters.dateFrom = null;
            activeFilters.dateTo = null;
            quickFilterBtns.forEach(function(b) { b.classList.remove('active'); });
            dateFromInput.value = '';
            dateToInput.value = '';
          } else if (type === 'date') {
            activeFilters.dateFrom = null;
            activeFilters.dateTo = null;
            dateFromInput.value = '';
            dateToInput.value = '';
          } else if (type === 'keyword') {
            activeFilters.keyword = '';
            keywordInput.value = '';
          }
          applyFilters();
        });
      });
      
      activeFiltersEl.style.display = 'flex';
    } else {
      activeFiltersEl.style.display = 'none';
    }
  }
  
  // Apply filters
  async function applyFilters() {
    console.log('[InlineFilters] applyFilters called with:', activeFilters);
    var hasFilters = activeFilters.datePreset || activeFilters.dateFrom || activeFilters.dateTo || activeFilters.keyword;
    
    if (!hasFilters) {
      console.log('[InlineFilters] No filters, resetting to paginated view');
      // Reset to paginated view
      if (filteredResultsEl) filteredResultsEl.style.display = 'none';
      if (paginatedContentEl) paginatedContentEl.style.display = 'block';
      if (activeFiltersEl) activeFiltersEl.style.display = 'none';
      return;
    }
    
    // Load and filter
    console.log('[InlineFilters] Loading search index...');
    var index = await loadSearchIndex();
    console.log('[InlineFilters] Search index loaded, total items:', index.length);
    
    var filtered = filterResults(index);
    console.log('[InlineFilters] Filtered results:', filtered.length);
    
    // Sort by date descending
    filtered.sort(function(a, b) { return new Date(b.date) - new Date(a.date); });
    
    // Show filtered results
    if (paginatedContentEl) paginatedContentEl.style.display = 'none';
    if (filteredResultsEl) filteredResultsEl.style.display = 'block';
    
    renderResults(filtered);
    updateActiveFiltersDisplay();
  }
  
  // Event handlers
  quickFilterBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      var preset = btn.dataset.filter;
      var isActive = btn.classList.contains('active');
      
      // Toggle off if clicking same button
      quickFilterBtns.forEach(function(b) { b.classList.remove('active'); });
      
      if (isActive) {
        activeFilters.datePreset = null;
        activeFilters.dateFrom = null;
        activeFilters.dateTo = null;
        dateFromInput.value = '';
        dateToInput.value = '';
      } else {
        btn.classList.add('active');
        activeFilters.datePreset = preset;
        var range = getDateRange(preset);
        activeFilters.dateFrom = formatDateForInput(range.from);
        activeFilters.dateTo = formatDateForInput(range.to);
        dateFromInput.value = activeFilters.dateFrom;
        dateToInput.value = activeFilters.dateTo;
      }
      
      applyFilters();
    });
  });
  
  // Date inputs
  dateFromInput.addEventListener('change', function() {
    activeFilters.datePreset = null;
    activeFilters.dateFrom = dateFromInput.value;
    quickFilterBtns.forEach(function(b) { b.classList.remove('active'); });
    applyFilters();
  });
  
  dateToInput.addEventListener('change', function() {
    activeFilters.datePreset = null;
    activeFilters.dateTo = dateToInput.value;
    quickFilterBtns.forEach(function(b) { b.classList.remove('active'); });
    applyFilters();
  });
  
  // Keyword
  keywordInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      activeFilters.keyword = keywordInput.value.trim();
      applyFilters();
    }
  });
  
  if (applyBtn) {
    applyBtn.addEventListener('click', function() {
      console.log('[InlineFilters] Apply button clicked, keyword:', keywordInput.value);
      activeFilters.keyword = keywordInput.value.trim();
      applyFilters();
    });
  } else {
    console.error('[InlineFilters] Apply button not found!');
  }
  
  // Clear all
  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      activeFilters = { datePreset: null, dateFrom: null, dateTo: null, keyword: '' };
      quickFilterBtns.forEach(function(b) { b.classList.remove('active'); });
      dateFromInput.value = '';
      dateToInput.value = '';
      keywordInput.value = '';
      applyFilters();
    });
  }
  
  // Reset button
  if (resetBtn) {
    resetBtn.addEventListener('click', function() {
      activeFilters = { datePreset: null, dateFrom: null, dateTo: null, keyword: '' };
      quickFilterBtns.forEach(function(b) { b.classList.remove('active'); });
      dateFromInput.value = '';
      dateToInput.value = '';
      keywordInput.value = '';
      if (filteredResultsEl) filteredResultsEl.style.display = 'none';
      if (paginatedContentEl) paginatedContentEl.style.display = 'block';
      if (activeFiltersEl) activeFiltersEl.style.display = 'none';
    });
  }
  
  console.log('[InlineFilters] Initialization complete');
});

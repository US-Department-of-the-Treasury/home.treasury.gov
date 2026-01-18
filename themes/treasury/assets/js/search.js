(function() {
  // State
  let searchIndex = null;
  let currentResults = [];
  let currentPage = 1;
  const perPage = 15;

  // DOM elements
  const formToggle = document.getElementById('form-toggle');
  const formContent = document.getElementById('form-content');
  const keywordInput = document.getElementById('search-keyword');
  const dateFromInput = document.getElementById('search-date-from');
  const dateToInput = document.getElementById('search-date-to');
  const typeSelect = document.getElementById('search-type');
  const adminSelect = document.getElementById('search-admin');
  const secretarySelect = document.getElementById('search-secretary');
  const topicSelect = document.getElementById('search-topic');
  const officeSelect = document.getElementById('search-office');
  const countrySelect = document.getElementById('search-country');
  const presetBtns = document.querySelectorAll('.preset-btn');
  const searchBtn = document.getElementById('run-search-btn');
  const resetBtn = document.getElementById('reset-search-btn');
  const modifySearchBtn = document.getElementById('modify-search-btn');
  const resultsArea = document.getElementById('search-results-area');
  const emptyState = document.getElementById('search-empty-state');
  const resultsList = document.getElementById('results-list');
  const resultsCount = document.getElementById('results-count');
  const resultsPagination = document.getElementById('results-pagination');

  // Form toggle functionality
  function collapseForm() {
    formContent.classList.add('collapsed');
    formToggle.setAttribute('aria-expanded', 'false');
  }

  function expandForm() {
    formContent.classList.remove('collapsed');
    formToggle.setAttribute('aria-expanded', 'true');
  }

  formToggle.addEventListener('click', function() {
    var isExpanded = formToggle.getAttribute('aria-expanded') === 'true';
    if (isExpanded) {
      collapseForm();
    } else {
      expandForm();
    }
  });

  // Modify search button - expand form
  modifySearchBtn.addEventListener('click', function() {
    expandForm();
    formContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  // Administration date ranges
  var adminDates = {
    'trump-2': { from: '2025-01-20', to: null },
    'biden': { from: '2021-01-20', to: '2025-01-19' },
    'trump-1': { from: '2017-01-20', to: '2021-01-19' },
    'obama': { from: '2009-01-20', to: '2017-01-19' }
  };

  // Secretary date ranges (approximate)
  var secretaryDates = {
    'bessent': { from: '2025-01-27', to: null },
    'yellen': { from: '2021-01-26', to: '2025-01-20' },
    'mnuchin': { from: '2017-02-13', to: '2021-01-20' },
    'lew': { from: '2013-02-28', to: '2017-01-20' },
    'geithner': { from: '2009-01-26', to: '2013-01-25' }
  };

  // Load search index
  function loadSearchIndex() {
    if (searchIndex) return Promise.resolve(searchIndex);
    return fetch('/index.json')
      .then(function(response) {
        return response.json();
      })
      .then(function(data) {
        searchIndex = data;
        return searchIndex;
      })
      .catch(function(error) {
        console.error('Failed to load search index:', error);
        return [];
      });
  }

  // Date helpers
  function getPresetDateRange(preset) {
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var result;

    switch (preset) {
      case 'today':
        return { from: today, to: today };
      case 'week':
        result = new Date(today);
        result.setDate(result.getDate() - 7);
        return { from: result, to: today };
      case 'month':
        result = new Date(today);
        result.setMonth(result.getMonth() - 1);
        return { from: result, to: today };
      case 'quarter':
        result = new Date(today);
        result.setMonth(result.getMonth() - 3);
        return { from: result, to: today };
      case 'year':
        result = new Date(today);
        result.setFullYear(result.getFullYear() - 1);
        return { from: result, to: today };
      default:
        return null;
    }
  }

  function formatDateForInput(date) {
    return date.toISOString().split('T')[0];
  }

  // Get current filters
  function getFilters() {
    return {
      keyword: keywordInput.value.trim(),
      dateFrom: dateFromInput.value,
      dateTo: dateToInput.value,
      type: typeSelect.value,
      admin: adminSelect.value,
      secretary: secretarySelect.value,
      topic: topicSelect.value,
      office: officeSelect.value,
      country: countrySelect.value
    };
  }

  // Filter results
  function filterResults(items, filters) {
    return items.filter(function(item) {
      // Keyword
      if (filters.keyword) {
        var searchText = (item.title + ' ' + (item.content || '')).toLowerCase();
        var keywords = filters.keyword.toLowerCase().split(/\s+/);
        var allMatch = keywords.every(function(kw) {
          return searchText.includes(kw);
        });
        if (!allMatch) return false;
      }

      // Date range
      var itemDate = new Date(item.date);
      if (filters.dateFrom && itemDate < new Date(filters.dateFrom)) return false;
      if (filters.dateTo) {
        var toDate = new Date(filters.dateTo);
        toDate.setHours(23, 59, 59, 999);
        if (itemDate > toDate) return false;
      }

      // Content type (section)
      if (filters.type) {
        var itemSection = item.section ? item.section.toLowerCase().replace(/\s+&?\s*/g, '-') : '';
        if (itemSection !== filters.type) return false;
      }

      // Administration (date-based)
      if (filters.admin && adminDates[filters.admin]) {
        var adminRange = adminDates[filters.admin];
        if (adminRange.from && itemDate < new Date(adminRange.from)) return false;
        if (adminRange.to && itemDate > new Date(adminRange.to)) return false;
      }

      // Secretary (date-based)
      if (filters.secretary && secretaryDates[filters.secretary]) {
        var secRange = secretaryDates[filters.secretary];
        if (secRange.from && itemDate < new Date(secRange.from)) return false;
        if (secRange.to && itemDate > new Date(secRange.to)) return false;
      }

      // Topic (if available in metadata)
      if (filters.topic && item.topics) {
        var topics = Array.isArray(item.topics) ? item.topics : [item.topics];
        var topicMatch = topics.some(function(t) {
          return t.toLowerCase().includes(filters.topic);
        });
        if (!topicMatch) return false;
      }

      // Office
      if (filters.office && item.offices) {
        var offices = Array.isArray(item.offices) ? item.offices : [item.offices];
        var officeMatch = offices.some(function(o) {
          return o.toLowerCase().includes(filters.office);
        });
        if (!officeMatch) return false;
      }

      // Country
      if (filters.country && item.countries) {
        var countries = Array.isArray(item.countries) ? item.countries : [item.countries];
        if (!countries.includes(filters.country)) return false;
      }

      return true;
    });
  }

  // Render a single item
  function renderItem(item) {
    var date = new Date(item.date);
    var dateStr = date.toLocaleDateString('en-US', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: 'numeric', minute: '2-digit'
    });

    var sectionHtml = item.section
      ? '<span class="article-category-divider">|</span><span class="article-category">' + item.section + '</span>'
      : '';

    return '<article class="news-article-item">' +
      '<div class="article-meta">' +
        '<time datetime="' + item.date + '">' + dateStr + ' EST</time>' +
        sectionHtml +
      '</div>' +
      '<h2><a href="' + item.url + '">' + item.title + '</a></h2>' +
    '</article>';
  }

  // Render results with pagination
  function renderResults(items, page) {
    currentResults = items;
    currentPage = page || 1;

    var totalPages = Math.ceil(items.length / perPage);
    var start = (currentPage - 1) * perPage;
    var end = start + perPage;
    var pageItems = items.slice(start, end);

    // Render items
    resultsList.innerHTML = pageItems.map(renderItem).join('');

    // Update count
    var showingStart = start + 1;
    var showingEnd = Math.min(end, items.length);
    resultsCount.textContent = 'Showing ' + showingStart + '-' + showingEnd + ' of ' + items.length + ' results';

    // Render pagination
    if (totalPages > 1) {
      renderPagination(totalPages);
    } else {
      resultsPagination.innerHTML = '';
      resultsPagination.style.display = 'none';
    }

    // Show results, hide empty state - with smooth transition
    if (resultsArea.style.display === 'none') {
      // First time showing results - fade in
      emptyState.style.display = 'none';
      resultsArea.classList.add('fade-out');
      resultsArea.style.display = 'block';
      // Force reflow then remove fade-out to trigger fade-in
      resultsArea.offsetHeight;
      resultsArea.classList.remove('fade-out');
    } else {
      // Already showing results, just update
      resultsArea.style.display = 'block';
      emptyState.style.display = 'none';
    }
  }

  // Render pagination controls
  function renderPagination(totalPages) {
    var html = '';

    // First button
    if (currentPage > 1) {
      html += '<button class="page-nav first" data-page="1">« First</button>';
    } else {
      html += '<span class="page-nav first disabled">« First</span>';
    }

    // Calculate window of 5 pages
    var startPage = 1;
    var endPage = totalPages;

    if (totalPages > 5) {
      startPage = currentPage - 2;
      if (startPage < 1) startPage = 1;
      endPage = startPage + 4;
      if (endPage > totalPages) {
        endPage = totalPages;
        startPage = endPage - 4;
      }
    }

    // Left ellipsis
    if (startPage > 1) {
      html += '<span class="page-ellipsis">...</span>';
    }

    // Page numbers
    for (var i = startPage; i <= endPage; i++) {
      if (i === currentPage) {
        html += '<span class="page-number current" aria-current="page">' + i + '</span>';
      } else {
        html += '<button class="page-number" data-page="' + i + '">' + i + '</button>';
      }
    }

    // Right ellipsis
    if (endPage < totalPages) {
      html += '<span class="page-ellipsis">...</span>';
    }

    // Last button
    if (currentPage < totalPages) {
      html += '<button class="page-nav last" data-page="' + totalPages + '">Last »</button>';
    } else {
      html += '<span class="page-nav last disabled">Last »</span>';
    }

    resultsPagination.innerHTML = html;
    resultsPagination.style.display = 'flex';

    // Add click handlers
    var pageButtons = resultsPagination.querySelectorAll('[data-page]');
    pageButtons.forEach(function(btn) {
      btn.addEventListener('click', function() {
        var page = parseInt(btn.dataset.page);
        renderResults(currentResults, page);
        // Scroll to top of results
        resultsArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  // Show validation message
  function showValidation(message) {
    var validationEl = document.getElementById('search-validation');
    if (!validationEl) {
      validationEl = document.createElement('div');
      validationEl.id = 'search-validation';
      validationEl.className = 'search-validation';
      searchBtn.parentNode.insertBefore(validationEl, searchBtn);
    }
    validationEl.textContent = message;
    validationEl.style.display = 'block';

    // Auto-hide after 5 seconds
    setTimeout(function() {
      validationEl.style.display = 'none';
    }, 5000);
  }

  // Build active filters summary
  function getActiveFiltersSummary(filters) {
    var tags = [];
    if (filters.keyword) tags.push({ type: 'keyword', label: '"' + filters.keyword + '"' });
    if (filters.dateFrom && filters.dateTo) {
      tags.push({ type: 'date', label: filters.dateFrom + ' to ' + filters.dateTo });
    } else if (filters.dateFrom) {
      tags.push({ type: 'date', label: 'From ' + filters.dateFrom });
    } else if (filters.dateTo) {
      tags.push({ type: 'date', label: 'Until ' + filters.dateTo });
    }
    if (filters.type) tags.push({ type: 'type', label: typeSelect.options[typeSelect.selectedIndex].text });
    if (filters.admin) tags.push({ type: 'admin', label: adminSelect.options[adminSelect.selectedIndex].text });
    if (filters.secretary) tags.push({ type: 'secretary', label: secretarySelect.options[secretarySelect.selectedIndex].text });
    if (filters.topic) tags.push({ type: 'topic', label: topicSelect.options[topicSelect.selectedIndex].text });
    if (filters.office) tags.push({ type: 'office', label: officeSelect.options[officeSelect.selectedIndex].text });
    if (filters.country) tags.push({ type: 'country', label: countrySelect.options[countrySelect.selectedIndex].text });
    return tags;
  }

  // Render filter tags
  function renderFilterTags(filters) {
    var tags = getActiveFiltersSummary(filters);
    var filterTagsEl = document.getElementById('active-filter-tags');

    if (tags.length === 0) {
      filterTagsEl.style.display = 'none';
      return;
    }

    var tagsHtml = tags.map(function(t) {
      return '<span class="filter-tag">' + t.label + '</span>';
    }).join('');

    filterTagsEl.innerHTML = '<span class="filter-tags-label">Active filters:</span>' + tagsHtml;
    filterTagsEl.style.display = 'flex';
  }

  // Set loading state
  function setLoading(loading) {
    if (loading) {
      searchBtn.disabled = true;
      searchBtn.innerHTML = '<svg class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<circle cx="12" cy="12" r="10" stroke-dasharray="32" stroke-dashoffset="12"></circle>' +
      '</svg> Searching...';
    } else {
      searchBtn.disabled = false;
      searchBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<circle cx="11" cy="11" r="8"></circle>' +
        '<path d="m21 21-4.35-4.35"></path>' +
      '</svg> Search';
    }
  }

  // Run search
  function runSearch() {
    var filters = getFilters();

    // Check if any filters are set
    var hasFilters = Object.keys(filters).some(function(key) {
      return filters[key];
    });

    if (!hasFilters) {
      showValidation('Please enter at least one search filter');
      return;
    }

    // Show loading state
    setLoading(true);

    loadSearchIndex().then(function(index) {
      var filtered = filterResults(index, filters);

      // Sort by date descending
      filtered.sort(function(a, b) {
        return new Date(b.date) - new Date(a.date);
      });

      // Hide loading
      setLoading(false);

      // If no results, show message but keep form expanded
      if (filtered.length === 0) {
        resultsArea.style.display = 'block';
        emptyState.style.display = 'none';
        resultsList.innerHTML = '<div class="no-results-message">No results found. Try adjusting your search criteria.</div>';
        resultsCount.textContent = '0 results';
        resultsPagination.innerHTML = '';
        resultsPagination.style.display = 'none';
        renderFilterTags(filters);
        // Keep form expanded so user can modify search
        return;
      }

      // Collapse the form and show results (NO auto-scroll - page stays stable)
      collapseForm();
      renderFilterTags(filters);
      renderResults(filtered, 1);

      // Hide empty state
      emptyState.style.display = 'none';
    });
  }

  // Event handlers
  presetBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      var preset = btn.dataset.preset;
      var isActive = btn.classList.contains('active');

      presetBtns.forEach(function(b) {
        b.classList.remove('active');
      });

      if (isActive) {
        dateFromInput.value = '';
        dateToInput.value = '';
      } else {
        btn.classList.add('active');
        var range = getPresetDateRange(preset);
        dateFromInput.value = formatDateForInput(range.from);
        dateToInput.value = formatDateForInput(range.to);
      }
    });
  });

  // Clear preset when manually changing dates
  dateFromInput.addEventListener('change', function() {
    presetBtns.forEach(function(b) {
      b.classList.remove('active');
    });
  });

  dateToInput.addEventListener('change', function() {
    presetBtns.forEach(function(b) {
      b.classList.remove('active');
    });
  });

  // Search button
  searchBtn.addEventListener('click', runSearch);

  // Enter key in keyword field
  keywordInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      runSearch();
    }
  });

  // Reset button - smooth transition
  resetBtn.addEventListener('click', function() {
    // Clear form fields immediately
    keywordInput.value = '';
    dateFromInput.value = '';
    dateToInput.value = '';
    typeSelect.value = '';
    adminSelect.value = '';
    secretarySelect.value = '';
    topicSelect.value = '';
    officeSelect.value = '';
    countrySelect.value = '';
    presetBtns.forEach(function(b) {
      b.classList.remove('active');
    });

    // Hide filter tags
    document.getElementById('active-filter-tags').style.display = 'none';

    // Expand the form first
    expandForm();

    // Smooth scroll to top of form
    formToggle.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // If results are showing, fade them out smoothly
    if (resultsArea.style.display !== 'none') {
      resultsArea.classList.add('fade-out');

      // After fade animation, hide results and show empty state
      setTimeout(function() {
        currentResults = [];
        currentPage = 1;
        resultsList.innerHTML = '';
        resultsPagination.innerHTML = '';
        resultsPagination.style.display = 'none';
        resultsArea.style.display = 'none';
        resultsArea.classList.remove('fade-out');

        // Show empty state with fade in
        emptyState.classList.add('fade-out');
        emptyState.style.display = 'block';
        // Force reflow then remove fade-out to trigger fade-in
        emptyState.offsetHeight;
        emptyState.classList.remove('fade-out');
      }, 250);
    } else {
      // Results weren't showing, just reset state
      currentResults = [];
      currentPage = 1;
    }
  });

  // Check for URL parameters on load and auto-search
  var urlParams = new URLSearchParams(window.location.search);
  var hasParams = false;

  if (urlParams.get('q')) {
    keywordInput.value = urlParams.get('q');
    hasParams = true;
  }
  if (urlParams.get('type')) {
    typeSelect.value = urlParams.get('type');
    hasParams = true;
  }
  if (urlParams.get('admin')) {
    adminSelect.value = urlParams.get('admin');
    hasParams = true;
  }
  if (urlParams.get('secretary')) {
    secretarySelect.value = urlParams.get('secretary');
    hasParams = true;
  }
  if (urlParams.get('topic')) {
    topicSelect.value = urlParams.get('topic');
    hasParams = true;
  }
  if (urlParams.get('office')) {
    officeSelect.value = urlParams.get('office');
    hasParams = true;
  }
  if (urlParams.get('country')) {
    countrySelect.value = urlParams.get('country');
    hasParams = true;
  }
  if (urlParams.get('from')) {
    dateFromInput.value = urlParams.get('from');
    hasParams = true;
  }
  if (urlParams.get('to')) {
    dateToInput.value = urlParams.get('to');
    hasParams = true;
  }

  // Auto-run search if parameters were passed
  if (hasParams) {
    runSearch();
  }
})();

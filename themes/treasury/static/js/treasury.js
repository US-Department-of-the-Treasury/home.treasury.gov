/**
 * U.S. Department of the Treasury
 * Site JavaScript
 */

(function() {
  'use strict';

  // ============================================
  // USA Banner toggle
  // ============================================
  const bannerButton = document.querySelector('.usa-banner-button');
  const bannerContent = document.getElementById('gov-banner-content');
  
  if (bannerButton && bannerContent) {
    bannerButton.addEventListener('click', function() {
      const expanded = this.getAttribute('aria-expanded') === 'true';
      this.setAttribute('aria-expanded', !expanded);
      bannerContent.hidden = expanded;
    });
  }

  // ============================================
  // Mega Menu Navigation (Click to Open)
  // ============================================
  const megaMenuButtons = document.querySelectorAll('.nav-item.has-dropdown > button.nav-link');
  let activeMegaMenu = null;
  
  function closeAllMegaMenus() {
    megaMenuButtons.forEach(btn => {
      btn.setAttribute('aria-expanded', 'false');
    });
    activeMegaMenu = null;
  }
  
  megaMenuButtons.forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      const isExpanded = this.getAttribute('aria-expanded') === 'true';
      const parentItem = this.closest('.nav-item');
      
      // Close all menus first
      closeAllMegaMenus();
      closeSearchDropdown();
      
      // Toggle this menu (open if was closed)
      if (!isExpanded) {
        this.setAttribute('aria-expanded', 'true');
        activeMegaMenu = parentItem;
      }
    });
  });
  
  // Close mega menus when clicking outside
  document.addEventListener('click', function(e) {
    if (activeMegaMenu && !e.target.closest('.nav-item.has-dropdown') && !e.target.closest('.mega-menu')) {
      closeAllMegaMenus();
    }
  });
  
  // Close mega menus when clicking inside mega menu links
  document.querySelectorAll('.mega-menu a').forEach(link => {
    link.addEventListener('click', function() {
      closeAllMegaMenus();
    });
  });

  // ============================================
  // Search Dropdown
  // ============================================
  const searchToggle = document.querySelector('.search-toggle');
  const searchDropdown = document.getElementById('search-dropdown');
  
  function closeSearchDropdown() {
    if (searchDropdown) {
      searchDropdown.hidden = true;
      searchToggle?.setAttribute('aria-expanded', 'false');
    }
  }
  
  function openSearchDropdown() {
    if (searchDropdown) {
      searchDropdown.hidden = false;
      searchToggle?.setAttribute('aria-expanded', 'true');
      const input = searchDropdown.querySelector('.search-input');
      if (input) input.focus();
    }
  }
  
  if (searchToggle) {
    searchToggle.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      const isExpanded = this.getAttribute('aria-expanded') === 'true';
      
      // Close mega menus
      closeAllMegaMenus();
      
      // Toggle search
      if (isExpanded) {
        closeSearchDropdown();
      } else {
        openSearchDropdown();
      }
    });
  }
  
  // Close search when clicking outside
  document.addEventListener('click', function(e) {
    if (searchDropdown && !searchDropdown.hidden && !e.target.closest('.nav-search')) {
      closeSearchDropdown();
    }
  });
  
  // Close all on Escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      closeAllMegaMenus();
      closeSearchDropdown();
    }
  });

  // ============================================
  // Hero Slider
  // ============================================
  const slides = document.querySelectorAll('.hero-slide');
  const dots = document.querySelectorAll('.slider-dot');
  let currentSlide = 0;
  let slideInterval;
  
  function showSlide(index) {
    slides.forEach((slide, i) => {
      slide.classList.toggle('active', i === index);
    });
    dots.forEach((dot, i) => {
      dot.classList.toggle('active', i === index);
    });
    currentSlide = index;
  }
  
  function nextSlide() {
    const next = (currentSlide + 1) % slides.length;
    showSlide(next);
  }
  
  if (slides.length > 1) {
    // Auto-advance slides every 6 seconds
    slideInterval = setInterval(nextSlide, 6000);
    
    // Dot click handlers
    dots.forEach((dot, i) => {
      dot.addEventListener('click', () => {
        clearInterval(slideInterval);
        showSlide(i);
        slideInterval = setInterval(nextSlide, 6000);
      });
    });
  }

  // ============================================
  // Mobile menu toggle
  // ============================================
  const mobileToggle = document.querySelector('.mobile-menu-toggle');
  const navMenu = document.querySelector('.nav-menu');
  
  if (mobileToggle && navMenu) {
    mobileToggle.addEventListener('click', function() {
      const expanded = this.getAttribute('aria-expanded') === 'true';
      this.setAttribute('aria-expanded', !expanded);
      navMenu.classList.toggle('is-open');
      document.body.classList.toggle('menu-open');
    });
  }

  // ============================================
  // News Filter - Client-side filtering
  // ============================================
  const filterForm = document.querySelector('.news-filter-form');
  const articleList = document.querySelector('.news-article-list');
  
  if (filterForm && articleList) {
    const articles = articleList.querySelectorAll('.news-article-item');
    const keywordInput = filterForm.querySelector('#keyword-search');
    const startDateInput = filterForm.querySelector('#start-date');
    const endDateInput = filterForm.querySelector('#end-date');
    const pagination = document.querySelector('.pagination');
    
    filterForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const keyword = keywordInput?.value.toLowerCase().trim() || '';
      const startDate = startDateInput?.value ? new Date(startDateInput.value) : null;
      const endDate = endDateInput?.value ? new Date(endDateInput.value) : null;
      
      let visibleCount = 0;
      
      articles.forEach(article => {
        const titleEl = article.querySelector('h2');
        const timeEl = article.querySelector('time');
        const title = titleEl?.textContent.toLowerCase() || '';
        const dateStr = timeEl?.getAttribute('datetime') || '';
        const articleDate = dateStr ? new Date(dateStr) : null;
        
        let show = true;
        
        // Keyword filter
        if (keyword && !title.includes(keyword)) {
          show = false;
        }
        
        // Date range filter
        if (show && articleDate) {
          if (startDate && articleDate < startDate) {
            show = false;
          }
          if (endDate && articleDate > endDate) {
            show = false;
          }
        }
        
        article.style.display = show ? '' : 'none';
        if (show) visibleCount++;
      });
      
      // Hide pagination when filtering
      if (pagination) {
        pagination.style.display = (keyword || startDate || endDate) ? 'none' : '';
      }
      
      // Show "no results" message if needed
      let noResultsMsg = articleList.querySelector('.no-results');
      if (visibleCount === 0) {
        if (!noResultsMsg) {
          noResultsMsg = document.createElement('p');
          noResultsMsg.className = 'no-results';
          noResultsMsg.style.cssText = 'padding: 2rem; text-align: center; color: #5c5c5c;';
          noResultsMsg.textContent = 'No results found. Try adjusting your search criteria.';
          articleList.appendChild(noResultsMsg);
        }
      } else if (noResultsMsg) {
        noResultsMsg.remove();
      }
      
      // Update URL with search params
      const params = new URLSearchParams();
      if (keyword) params.set('title', keyword);
      if (startDateInput?.value) params.set('publication-start-date', startDateInput.value);
      if (endDateInput?.value) params.set('publication-end-date', endDateInput.value);
      
      const newUrl = params.toString() 
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname;
      window.history.replaceState({}, '', newUrl);
    });
    
    // Pre-fill form from URL params
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('title') || urlParams.has('publication-start-date') || urlParams.has('publication-end-date')) {
      if (keywordInput && urlParams.has('title')) {
        keywordInput.value = urlParams.get('title');
      }
      if (startDateInput && urlParams.has('publication-start-date')) {
        startDateInput.value = urlParams.get('publication-start-date');
      }
      if (endDateInput && urlParams.has('publication-end-date')) {
        endDateInput.value = urlParams.get('publication-end-date');
      }
      filterForm.dispatchEvent(new Event('submit'));
    }
  }

  // ============================================
  // External link handling
  // ============================================
  const externalLinks = document.querySelectorAll('a[href^="http"]:not([href*="' + window.location.hostname + '"])');
  
  externalLinks.forEach(function(link) {
    if (!link.hasAttribute('target')) {
      link.setAttribute('target', '_blank');
      link.setAttribute('rel', 'noopener noreferrer');
    }
  });

})();

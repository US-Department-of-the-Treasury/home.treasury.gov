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
  // Mega Menu Navigation
  // ============================================
  const navToggles = document.querySelectorAll('.nav-toggle');
  let activeDropdown = null;
  
  function closeAllDropdowns() {
    navToggles.forEach(toggle => {
      toggle.setAttribute('aria-expanded', 'false');
      const dropdownId = toggle.getAttribute('aria-controls');
      const dropdown = document.getElementById(dropdownId);
      if (dropdown) {
        dropdown.hidden = true;
      }
    });
    activeDropdown = null;
  }
  
  navToggles.forEach(toggle => {
    toggle.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      
      const dropdownId = this.getAttribute('aria-controls');
      const dropdown = document.getElementById(dropdownId);
      const isExpanded = this.getAttribute('aria-expanded') === 'true';
      
      // Close all other dropdowns first
      if (!isExpanded) {
        closeAllDropdowns();
      }
      
      // Toggle this dropdown
      this.setAttribute('aria-expanded', !isExpanded);
      if (dropdown) {
        dropdown.hidden = isExpanded;
        activeDropdown = isExpanded ? null : dropdown;
      }
    });
  });
  
  // Close dropdowns when clicking outside
  document.addEventListener('click', function(e) {
    if (activeDropdown && !e.target.closest('.nav-item')) {
      closeAllDropdowns();
    }
  });
  
  // Close dropdowns on Escape key
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && activeDropdown) {
      closeAllDropdowns();
    }
  });

  // ============================================
  // Search Overlay
  // ============================================
  const searchToggle = document.querySelector('.search-toggle');
  const searchOverlay = document.getElementById('search-overlay');
  const searchClose = document.querySelector('.search-overlay-close');
  const searchInput = document.querySelector('.search-overlay-input');
  
  function openSearchOverlay() {
    if (searchOverlay) {
      searchOverlay.hidden = false;
      searchToggle?.setAttribute('aria-expanded', 'true');
      searchInput?.focus();
      document.body.style.overflow = 'hidden';
    }
  }
  
  function closeSearchOverlay() {
    if (searchOverlay) {
      searchOverlay.hidden = true;
      searchToggle?.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    }
  }
  
  if (searchToggle) {
    searchToggle.addEventListener('click', function() {
      const isExpanded = this.getAttribute('aria-expanded') === 'true';
      if (isExpanded) {
        closeSearchOverlay();
      } else {
        closeAllDropdowns(); // Close any open mega menus
        openSearchOverlay();
      }
    });
  }
  
  if (searchClose) {
    searchClose.addEventListener('click', closeSearchOverlay);
  }
  
  // Close search overlay on Escape
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && searchOverlay && !searchOverlay.hidden) {
      closeSearchOverlay();
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
    
    // Store original articles for resetting
    const originalArticles = Array.from(articles);
    
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
      
      // Update URL with search params (without navigation)
      const params = new URLSearchParams();
      if (keyword) params.set('title', keyword);
      if (startDateInput?.value) params.set('publication-start-date', startDateInput.value);
      if (endDateInput?.value) params.set('publication-end-date', endDateInput.value);
      
      const newUrl = params.toString() 
        ? `${window.location.pathname}?${params.toString()}`
        : window.location.pathname;
      window.history.replaceState({}, '', newUrl);
    });
    
    // Pre-fill form from URL params and trigger filter
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
      // Trigger filter on page load if params exist
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

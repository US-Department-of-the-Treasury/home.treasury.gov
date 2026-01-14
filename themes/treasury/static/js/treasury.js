/**
 * U.S. Department of the Treasury
 * Site JavaScript
 */

(function() {
  'use strict';

  // ============================================
  // Sticky Nav - Show logo when scrolled
  // ============================================
  const mainNav = document.querySelector('.main-nav');
  const header = document.getElementById('header');
  
  if (mainNav && header) {
    function handleScroll() {
      const headerBottom = header.offsetTop + header.offsetHeight;
      if (window.scrollY >= headerBottom) {
        mainNav.classList.add('scrolled');
      } else {
        mainNav.classList.remove('scrolled');
      }
    }
    
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Check on load
  }

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
  
  // Close all on Escape and return focus to trigger
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      // Return focus to active mega menu button if one was open
      if (activeMegaMenu) {
        const triggerBtn = activeMegaMenu.querySelector('button.nav-link');
        closeAllMegaMenus();
        if (triggerBtn) triggerBtn.focus();
      }
      // Return focus to search toggle if search was open
      if (searchDropdown && !searchDropdown.hidden) {
        closeSearchDropdown();
        if (searchToggle) searchToggle.focus();
      }
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
  // News Filter - Submits to live Treasury site
  // ============================================
  // Form action is set in the HTML template to submit to
  // https://home.treasury.gov/news/press-releases/ (or current section)
  // No client-side interception needed.

})();

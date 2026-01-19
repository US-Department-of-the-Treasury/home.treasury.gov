/**
 * Treasury Year in Review - Interactive Components
 * Handles accordion functionality, keyboard navigation, and URL hash state
 */

(function() {
  'use strict';

  // DOM Elements
  const accordions = document.querySelectorAll('.accordion');
  const accordionHeaders = document.querySelectorAll('.accordion-header');

  /**
   * Initialize accordions with proper ARIA attributes
   */
  function initAccordions() {
    accordions.forEach((accordion, index) => {
      const header = accordion.querySelector('.accordion-header');
      const content = accordion.querySelector('.accordion-content');
      const contentId = `accordion-content-${index}`;

      // Set ARIA attributes
      content.id = contentId;
      header.setAttribute('aria-controls', contentId);
      header.setAttribute('aria-expanded', accordion.open ? 'true' : 'false');

      // Update ARIA on toggle
      accordion.addEventListener('toggle', () => {
        header.setAttribute('aria-expanded', accordion.open ? 'true' : 'false');

        // Update URL hash when opening
        if (accordion.open && accordion.id) {
          history.replaceState(null, '', `#${accordion.id}`);
        }
      });
    });
  }

  /**
   * Handle keyboard navigation between accordions
   */
  function initKeyboardNavigation() {
    accordionHeaders.forEach((header, index) => {
      header.addEventListener('keydown', (e) => {
        let targetIndex;

        switch (e.key) {
          case 'ArrowDown':
          case 'j':
            e.preventDefault();
            targetIndex = (index + 1) % accordionHeaders.length;
            accordionHeaders[targetIndex].focus();
            break;

          case 'ArrowUp':
          case 'k':
            e.preventDefault();
            targetIndex = (index - 1 + accordionHeaders.length) % accordionHeaders.length;
            accordionHeaders[targetIndex].focus();
            break;

          case 'Home':
            e.preventDefault();
            accordionHeaders[0].focus();
            break;

          case 'End':
            e.preventDefault();
            accordionHeaders[accordionHeaders.length - 1].focus();
            break;
        }
      });
    });

    // Global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      // Number keys 1-4 to jump to sections
      if (e.key >= '1' && e.key <= '4' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const target = document.activeElement;
        // Only if not focused on an input
        if (target.tagName !== 'INPUT' && target.tagName !== 'TEXTAREA') {
          const index = parseInt(e.key) - 1;
          if (accordions[index]) {
            e.preventDefault();
            accordions[index].open = true;
            accordionHeaders[index].focus();
            accordions[index].scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }
      }

      // Escape to close all accordions
      if (e.key === 'Escape') {
        accordions.forEach(accordion => {
          accordion.open = false;
        });
      }
    });
  }

  /**
   * Handle URL hash on page load
   */
  function handleHashNavigation() {
    const hash = window.location.hash.slice(1);
    if (hash) {
      const targetAccordion = document.getElementById(hash);
      if (targetAccordion && targetAccordion.classList.contains('accordion')) {
        // Small delay to ensure page is rendered
        setTimeout(() => {
          targetAccordion.open = true;
          targetAccordion.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
      }
    }
  }

  /**
   * Handle hash changes (e.g., clicking anchor links)
   */
  function initHashChangeListener() {
    window.addEventListener('hashchange', () => {
      handleHashNavigation();
    });
  }

  /**
   * Initialize all functionality
   */
  function init() {
    initAccordions();
    initKeyboardNavigation();
    handleHashNavigation();
    initHashChangeListener();
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

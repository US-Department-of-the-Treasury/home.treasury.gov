/**
 * Service Worker Registration
 * Handles offline caching and PWA functionality
 */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', function() {
    navigator.serviceWorker.register('/sw.js').catch(function(err) {
      console.log('SW registration failed:', err);
    });
  });
}

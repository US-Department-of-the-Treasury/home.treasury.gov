// Redirect /news/ to /news/press-releases/
(function() {
  if (window.location.pathname === '/news/' || window.location.pathname === '/news') {
    window.location.replace('/news/press-releases/');
  }
})();

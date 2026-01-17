// Redirect 404 pages to the live Treasury site
(function() {
  var currentPath = window.location.pathname + window.location.search;
  var treasuryUrl = 'https://home.treasury.gov' + currentPath;
  window.location.replace(treasuryUrl);
})();

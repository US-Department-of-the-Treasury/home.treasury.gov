// Pagination jump-to-page functionality
(function() {
  // Find all page-jump forms and attach handlers
  var forms = document.querySelectorAll('.page-jump');

  forms.forEach(function(form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();

      var input = form.querySelector('input');
      var baseURL = form.dataset.baseUrl;
      var totalPages = parseInt(form.dataset.totalPages, 10);
      var page = parseInt(input.value, 10);

      if (page >= 1 && page <= totalPages) {
        if (page === 1) {
          window.location.href = baseURL;
        } else {
          window.location.href = baseURL + 'page/' + page + '/';
        }
      } else {
        alert('Please enter a page number between 1 and ' + totalPages);
      }
    });
  });
})();

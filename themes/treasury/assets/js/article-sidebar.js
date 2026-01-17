// Article Sidebar - Load and display article metadata
(function() {
  var currentUrl = window.location.pathname;
  var metadataContent = document.getElementById('metadata-content');
  var metadataLoading = document.getElementById('metadata-loading');

  // Exit early if elements don't exist
  if (!metadataContent || !metadataLoading) return;

  // Admin labels
  var adminLabels = {
    'trump2': 'Trump Administration II',
    'biden': 'Biden Administration',
    'trump1': 'Trump Administration I',
    'obama': 'Obama Administration'
  };

  // Secretary labels
  var secretaryLabels = {
    'bessent': 'Scott Bessent',
    'yellen': 'Janet Yellen',
    'mnuchin': 'Steven Mnuchin',
    'lew': 'Jack Lew',
    'geithner': 'Timothy Geithner'
  };

  // Topic labels
  var topicLabels = {
    'sanctions': 'Sanctions & OFAC',
    'tax': 'Tax Policy',
    'economy': 'Economic Policy',
    'debt': 'Debt & Budget',
    'financial': 'Financial Regulation',
    'fincrime': 'Financial Crimes',
    'terrorism': 'Terrorism & Illicit Finance',
    'international': 'International Affairs',
    'climate': 'Climate & Energy',
    'recovery': 'Economic Recovery',
    'currency': 'Currency & Monetary Policy',
    'covid': 'COVID-19 Response'
  };

  // Country labels with flags
  var countryLabels = {
    'russia': { label: 'Russia', flag: '🇷🇺' },
    'china': { label: 'China', flag: '🇨🇳' },
    'iran': { label: 'Iran', flag: '🇮🇷' },
    'northkorea': { label: 'North Korea', flag: '🇰🇵' },
    'ukraine': { label: 'Ukraine', flag: '🇺🇦' },
    'venezuela': { label: 'Venezuela', flag: '🇻🇪' },
    'syria': { label: 'Syria', flag: '🇸🇾' },
    'cuba': { label: 'Cuba', flag: '🇨🇺' },
    'myanmar': { label: 'Myanmar', flag: '🇲🇲' },
    'afghanistan': { label: 'Afghanistan', flag: '🇦🇫' }
  };

  // Office labels
  var officeLabels = {
    'ofac': 'OFAC',
    'fincen': 'FinCEN',
    'irs': 'IRS',
    'occ': 'OCC',
    'fiscal': 'Fiscal Service',
    'mint': 'U.S. Mint',
    'bep': 'BEP',
    'international-affairs': 'International Affairs'
  };

  // Render metadata
  function renderMetadata(article) {
    var html = '';

    // Published Date & Time
    if (article.dateTimeDisplay) {
      html += '<div class="metadata-group">' +
        '<span class="metadata-label">Published</span>' +
        '<span class="metadata-value">' + article.dateTimeDisplay + '</span>' +
      '</div>';
    } else if (article.dateDisplay) {
      html += '<div class="metadata-group">' +
        '<span class="metadata-label">Published</span>' +
        '<span class="metadata-value">' + article.dateDisplay + '</span>' +
      '</div>';
    }

    // Section/Type
    if (article.section) {
      var sectionSlug = article.section.toLowerCase().replace(/\s+&?\s*/g, '-');
      html += '<div class="metadata-group">' +
        '<span class="metadata-label">Category</span>' +
        '<div class="metadata-tags">' +
          '<a href="/news/search/?type=' + sectionSlug + '" class="metadata-tag metadata-tag--section">' + article.section + '</a>' +
        '</div>' +
      '</div>';
    }

    // Administration
    if (article.president) {
      var adminLabel = adminLabels[article.president] || article.president;
      html += '<div class="metadata-group">' +
        '<span class="metadata-label">Administration</span>' +
        '<div class="metadata-tags">' +
          '<a href="/news/search/?admin=' + article.president + '" class="metadata-tag metadata-tag--admin">' + adminLabel + '</a>' +
        '</div>' +
      '</div>';
    }

    // Secretary
    if (article.secretary) {
      var secLabel = secretaryLabels[article.secretary] || article.secretary;
      html += '<div class="metadata-group">' +
        '<span class="metadata-label">Treasury Secretary</span>' +
        '<div class="metadata-tags">' +
          '<a href="/news/search/?secretary=' + article.secretary + '" class="metadata-tag metadata-tag--secretary">' + secLabel + '</a>' +
        '</div>' +
      '</div>';
    }

    // Topics
    if (article.topics && article.topics.length > 0) {
      var topicTags = article.topics.map(function(t) {
        var label = topicLabels[t] || t;
        return '<a href="/news/search/?topic=' + t + '" class="metadata-tag metadata-tag--topic">' + label + '</a>';
      }).join('');

      html += '<div class="metadata-group">' +
        '<span class="metadata-label">Topics</span>' +
        '<div class="metadata-tags">' + topicTags + '</div>' +
      '</div>';
    }

    // Offices
    if (article.offices && article.offices.length > 0) {
      var officeTags = article.offices.map(function(o) {
        var label = officeLabels[o] || o.toUpperCase();
        return '<a href="/news/search/?office=' + o + '" class="metadata-tag metadata-tag--office">' + label + '</a>';
      }).join('');

      html += '<div class="metadata-group">' +
        '<span class="metadata-label">Treasury Offices</span>' +
        '<div class="metadata-tags">' + officeTags + '</div>' +
      '</div>';
    }

    // Countries
    if (article.countries && article.countries.length > 0) {
      var countryTags = article.countries.map(function(c) {
        var info = countryLabels[c] || { label: c, flag: '' };
        var flagSpan = info.flag ? '<span class="country-flag">' + info.flag + '</span> ' : '';
        return '<a href="/news/search/?country=' + c + '" class="metadata-tag metadata-tag--country">' + flagSpan + info.label + '</a>';
      }).join('');

      html += '<div class="metadata-group">' +
        '<span class="metadata-label">Countries Mentioned</span>' +
        '<div class="metadata-tags">' + countryTags + '</div>' +
      '</div>';
    }

    return html;
  }

  // Load article metadata
  function loadMetadata() {
    fetch('/index.json')
      .then(function(response) {
        return response.json();
      })
      .then(function(index) {
        // Find current article
        var article = index.find(function(item) {
          return item.url === currentUrl;
        });

        if (article) {
          metadataContent.innerHTML = renderMetadata(article);
          metadataContent.style.display = 'flex';
          metadataLoading.style.display = 'none';
        } else {
          metadataLoading.textContent = 'Metadata not available';
        }
      })
      .catch(function(error) {
        console.error('Failed to load metadata:', error);
        metadataLoading.textContent = 'Failed to load metadata';
      });
  }

  loadMetadata();
})();

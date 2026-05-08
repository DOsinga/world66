// Unsplash city-level slideshow
// Finds all [data-unsplash] elements and loads a slideshow of inspiring photos.
// Elements must already have a background-image or be a plain div.
(function() {
  'use strict';

  function buildSlideshow(el, urls) {
    if (!urls.length) return;
    var idx = 0;
    var timer = null;

    function show(n) {
      idx = (n + urls.length) % urls.length;
      var img = new Image();
      img.onload = function() {
        el.style.backgroundImage = "url('" + urls[idx] + "')";
        updateDots();
      };
      img.src = urls[idx];
    }

    // Dots
    var dots = document.createElement('div');
    dots.className = 'us-dots';
    urls.forEach(function(_, i) {
      var d = document.createElement('span');
      d.className = 'us-dot' + (i === 0 ? ' active' : '');
      dots.appendChild(d);
    });
    el.appendChild(dots);

    function updateDots() {
      dots.querySelectorAll('.us-dot').forEach(function(d, i) {
        d.classList.toggle('active', i === idx);
      });
    }

    // Load first image (cross-fade in)
    show(0);

    // Auto-advance
    function next() { show(idx + 1); }
    timer = setInterval(next, 5000);

    // Click to advance
    el.addEventListener('click', function(e) {
      if (e.target.closest('.plan-dest-tile-overlay, a')) return;
      clearInterval(timer);
      show(idx + 1);
      timer = setInterval(next, 5000);
    });
  }

  document.querySelectorAll('[data-unsplash]').forEach(function(el) {
    var query = el.dataset.unsplash;
    if (!query) return;
    fetch('/api/unsplash-images?query=' + encodeURIComponent(query))
      .then(function(r) { return r.json(); })
      .then(function(data) { buildSlideshow(el, data.urls || []); })
      .catch(function() {});
  });
})();

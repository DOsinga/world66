// Unsplash city-level slideshow — loads only on user click
(function() {
  'use strict';

  function buildSlideshow(el, urls) {
    var idx = 0;
    var timer = null;

    // Dots
    var dots = document.createElement('div');
    dots.className = 'us-dots';
    urls.forEach(function(_, i) {
      var d = document.createElement('span');
      d.className = 'us-dot' + (i === 0 ? ' active' : '');
      dots.appendChild(d);
    });
    el.appendChild(dots);

    function show(n) {
      idx = (n + urls.length) % urls.length;
      var img = new Image();
      img.onload = function() {
        el.style.backgroundImage = "url('" + urls[idx] + "')";
        el.classList.remove('us-loading');
        dots.querySelectorAll('.us-dot').forEach(function(d, i) {
          d.classList.toggle('active', i === idx);
        });
      };
      img.src = urls[idx];
    }

    show(0);
    timer = setInterval(function() { show(idx + 1); }, 5000);

    el.addEventListener('click', function(e) {
      if (e.target.closest('.plan-dest-tile-overlay, a')) return;
      clearInterval(timer);
      show(idx + 1);
      timer = setInterval(function() { show(idx + 1); }, 5000);
    });
  }

  document.querySelectorAll('[data-unsplash]').forEach(function(el) {
    var query = el.dataset.unsplash;
    if (!query) return;

    // Show camera hint
    var hint = document.createElement('div');
    hint.className = 'us-hint';
    hint.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>';
    el.appendChild(hint);

    var loaded = false;
    el.addEventListener('click', function(e) {
      if (e.target.closest('.plan-dest-tile-overlay, a')) return;
      if (loaded) return;
      loaded = true;
      hint.remove();
      el.classList.add('us-loading');
      fetch('/api/unsplash-images?query=' + encodeURIComponent(query))
        .then(function(r) { return r.json(); })
        .then(function(data) {
          var urls = data.urls || [];
          if (urls.length) buildSlideshow(el, urls);
          else el.classList.remove('us-loading');
        })
        .catch(function() { el.classList.remove('us-loading'); });
    }, { once: false });
  });
})();

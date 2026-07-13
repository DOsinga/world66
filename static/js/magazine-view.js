(function() {
  var overlay = document.getElementById('magazine-overlay');
  if (!overlay) return;

  var openBtn = document.querySelector('[data-magazine-open]');
  var closeBtn = document.getElementById('magazine-close');
  var shuffleBtn = document.getElementById('magazine-shuffle');
  var prevBtn = document.getElementById('magazine-prev');
  var nextBtn = document.getElementById('magazine-next');
  var spreadsWrap = document.getElementById('magazine-spreads');
  var docBody = document.body;
  var mapIdCounter = 0;

  function spreads() {
    return Array.prototype.slice.call(spreadsWrap.querySelectorAll('[data-magazine-spread]'));
  }

  function openOverlay() {
    overlay.classList.add('is-open');
    overlay.setAttribute('aria-hidden', 'false');
    docBody.classList.add('magazine-open');
  }

  function closeOverlay() {
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    docBody.classList.remove('magazine-open');
  }

  function step(dir) {
    spreadsWrap.scrollBy({left: dir * spreadsWrap.clientWidth, behavior: 'smooth'});
  }

  function shuffle() {
    var shuffled = spreads().sort(function() { return Math.random() - 0.5; });
    shuffled.forEach(function(el) { spreadsWrap.appendChild(el); });
    spreadsWrap.scrollTo({left: 0});
  }

  function renderPoisAndMap(spread, data) {
    var pois = data.pois || [];
    if (!pois.length) return;

    var poisWrap = spread.querySelector('.magazine-article-pois');
    var list = spread.querySelector('.magazine-article-poi-list');
    poisWrap.hidden = false;

    // pois arrives sorted best-first; give the top one the "cover story"
    // treatment (bigger tile, bigger image, full snippet) in the 3-col grid.
    pois.forEach(function(poi, i) {
      var featured = i === 0;
      var li = document.createElement('li');
      li.className = 'magazine-poi-item' + (featured ? ' magazine-poi-item--featured' : '');
      var a = document.createElement('a');
      a.href = poi.url;
      a.className = 'magazine-poi-link';
      var thumb = poi.image_url
        ? '<img src="' + poi.image_url + '" alt="" class="magazine-poi-thumb">'
        : '<span class="magazine-poi-thumb magazine-poi-thumb--none"></span>';
      a.innerHTML = thumb
        + '<span class="magazine-poi-meat">'
        + (featured ? '<span class="magazine-poi-kicker">Don\'t miss</span>' : '')
        + '<span class="magazine-poi-name">' + (poi.name || '') + '</span>'
        + (poi.snippet ? '<span class="magazine-poi-snippet">' + poi.snippet + '</span>' : '')
        + '</span>';
      li.appendChild(a);
      list.appendChild(li);
    });

    // A small, playful map — rounded, tilted frame — reusing the same
    // Leaflet setup as the sidebar map (world66map.js). initLocationMap
    // looks its container up by document.getElementById internally, so it
    // needs a real, unique string id, not just an element reference.
    if (typeof initLocationMap === 'function' && typeof data.lat === 'number') {
      var mapEl = spread.querySelector('.magazine-article-map');
      mapEl.id = 'magazine-map-' + (mapIdCounter++);
      var markers = [{lat: data.lat, lng: data.lng, name: data.title, highlight: true}]
        .concat(pois.map(function(p) { return {lat: p.lat, lng: p.lng, name: p.name, url: p.url}; }));
      requestAnimationFrame(function() {
        initLocationMap(mapEl.id, markers, {});
      });
    }
  }

  function loadArticle(spread) {
    if (spread.getAttribute('data-loaded') === '1') return;
    spread.setAttribute('data-loaded', '1');

    var path = spread.getAttribute('data-path');
    var contentEl = spread.querySelector('.magazine-article-content');
    contentEl.classList.add('is-loading');

    fetch('/api/page-content/' + path)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        contentEl.classList.remove('is-loading');
        contentEl.innerHTML = data.body_html || '';
        renderPoisAndMap(spread, data);
      })
      .catch(function() {
        contentEl.classList.remove('is-loading');
        var teaserEl = spread.querySelector('.magazine-spread-teaser');
        contentEl.textContent = teaserEl ? teaserEl.textContent : '';
      });
  }

  // Scrolling down within a spread reveals its full article in place;
  // scrolling back up returns to the cover (pure CSS scroll-snap, no JS
  // needed for the "go back" half). We only need to lazily fetch the
  // article body the first time someone scrolls far enough into it.
  spreads().forEach(function(spread) {
    var scroller = spread.querySelector('.magazine-spread-scroll');
    scroller.addEventListener('scroll', function() {
      if (scroller.scrollTop > scroller.clientHeight * 0.2) {
        loadArticle(spread);
      }
    });
  });

  if (openBtn) openBtn.addEventListener('click', openOverlay);
  if (closeBtn) closeBtn.addEventListener('click', closeOverlay);
  if (shuffleBtn) shuffleBtn.addEventListener('click', shuffle);
  if (prevBtn) prevBtn.addEventListener('click', function() { step(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function() { step(1); });

  // Horizontal gestures (trackpad two-finger swipe, shift+wheel) move
  // between spreads. Plain vertical wheel is left alone so it scrolls the
  // active spread's own cover-to-article content instead of the strip.
  // One gesture = one step: a fast/long swipe fires dozens of wheel events
  // with large deltas, so following deltaX 1:1 felt wildly oversensitive
  // (a single swipe could blow past several spreads). Instead, the first
  // event past the threshold advances exactly one spread, then a short
  // cooldown ignores the rest of that same gesture.
  var wheelCooldown = false;
  spreadsWrap.addEventListener('wheel', function(e) {
    if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
    e.preventDefault();
    if (wheelCooldown || Math.abs(e.deltaX) < 8) return;
    wheelCooldown = true;
    step(e.deltaX > 0 ? 1 : -1);
    setTimeout(function() { wheelCooldown = false; }, 650);
  }, {passive: false});

  document.addEventListener('keydown', function(e) {
    if (!overlay.classList.contains('is-open')) return;
    if (e.key === 'Escape') {
      closeOverlay();
    } else if (e.key === 'ArrowLeft') {
      step(-1);
    } else if (e.key === 'ArrowRight') {
      step(1);
    }
  });
})();

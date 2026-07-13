(function() {
  var overlay = document.getElementById('magazine-overlay');
  if (!overlay) return;

  var openBtn = document.querySelector('[data-magazine-open]');
  var closeBtn = document.getElementById('magazine-close');
  var shuffleBtn = document.getElementById('magazine-shuffle');
  var backBtn = document.getElementById('magazine-back');
  var prevBtn = document.getElementById('magazine-prev');
  var nextBtn = document.getElementById('magazine-next');
  var spreadsWrap = document.getElementById('magazine-spreads');
  var article = document.getElementById('magazine-article');
  var articleImg = document.getElementById('magazine-article-img');
  var articleTitle = document.getElementById('magazine-article-title');
  var articleContent = document.getElementById('magazine-article-content');
  var articlePois = document.getElementById('magazine-article-pois');
  var articlePoiList = document.getElementById('magazine-article-poi-list');
  var docBody = document.body;
  var articleMap = null;

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
    closeArticle();
  }

  function step(dir) {
    spreadsWrap.scrollBy({left: dir * spreadsWrap.clientWidth, behavior: 'smooth'});
  }

  function shuffle() {
    var shuffled = spreads().sort(function() { return Math.random() - 0.5; });
    shuffled.forEach(function(el) { spreadsWrap.appendChild(el); });
    spreadsWrap.scrollTo({left: 0});
  }

  function clearArticleMap() {
    if (articleMap) {
      articleMap.remove();
      articleMap = null;
    }
  }

  function renderPoisAndMap(data) {
    var pois = data.pois || [];
    articlePoiList.innerHTML = '';
    clearArticleMap();

    if (!pois.length) {
      articlePois.hidden = true;
      return;
    }
    articlePois.hidden = false;

    pois.forEach(function(poi) {
      var li = document.createElement('li');
      li.className = 'magazine-poi-item';
      var a = document.createElement('a');
      a.href = poi.url;
      a.className = 'magazine-poi-link';
      var thumb = poi.image_url
        ? '<img src="' + poi.image_url + '" alt="" class="magazine-poi-thumb">'
        : '<span class="magazine-poi-thumb magazine-poi-thumb--none"></span>';
      a.innerHTML = thumb
        + '<span class="magazine-poi-meat">'
        + '<span class="magazine-poi-name">' + (poi.name || '') + '</span>'
        + (poi.snippet ? '<span class="magazine-poi-snippet">' + poi.snippet + '</span>' : '')
        + '</span>';
      li.appendChild(a);
      articlePoiList.appendChild(li);
    });

    // A small, playful map centred on this destination plus its top POIs —
    // reuses the same Leaflet setup as the sidebar map (world66map.js).
    if (typeof initLocationMap === 'function' && typeof data.lat === 'number') {
      var markers = [{lat: data.lat, lng: data.lng, name: data.title, highlight: true}]
        .concat(pois.map(function(p) { return {lat: p.lat, lng: p.lng, name: p.name, url: p.url}; }));
      requestAnimationFrame(function() {
        articleMap = initLocationMap('magazine-article-map', markers, {});
      });
    }
  }

  function openArticle(spread) {
    var path = spread.getAttribute('data-path');
    var title = spread.getAttribute('data-title');
    var img = spread.querySelector('img');

    articleTitle.textContent = title || '';
    articleContent.innerHTML = '';
    articleContent.classList.add('is-loading');
    articlePois.hidden = true;
    articlePoiList.innerHTML = '';
    clearArticleMap();
    if (img) {
      articleImg.src = img.src;
      articleImg.alt = title || '';
      articleImg.parentElement.classList.remove('no-image');
    } else {
      articleImg.parentElement.classList.add('no-image');
    }

    article.hidden = false;
    backBtn.hidden = false;
    shuffleBtn.hidden = true;
    article.scrollTop = 0;

    fetch('/api/page-content/' + path)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        articleContent.classList.remove('is-loading');
        articleContent.innerHTML = data.body_html || '';
        if (!img && data.image_url) {
          articleImg.src = data.image_url;
          articleImg.alt = data.title || '';
          articleImg.parentElement.classList.remove('no-image');
        }
        renderPoisAndMap(data);
      })
      .catch(function() {
        articleContent.classList.remove('is-loading');
        var teaserEl = spread.querySelector('.magazine-spread-teaser');
        articleContent.textContent = teaserEl ? teaserEl.textContent : '';
      });
  }

  function closeArticle() {
    article.hidden = true;
    backBtn.hidden = true;
    shuffleBtn.hidden = false;
    clearArticleMap();
  }

  if (openBtn) openBtn.addEventListener('click', openOverlay);
  if (closeBtn) closeBtn.addEventListener('click', closeOverlay);
  if (shuffleBtn) shuffleBtn.addEventListener('click', shuffle);
  if (backBtn) backBtn.addEventListener('click', closeArticle);
  if (prevBtn) prevBtn.addEventListener('click', function() { step(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function() { step(1); });

  spreadsWrap.addEventListener('click', function(e) {
    var spread = e.target.closest('[data-magazine-spread]');
    if (!spread) return;
    e.preventDefault();
    openArticle(spread);
  });

  // Mouse-wheel over the strip scrolls it horizontally (native on touch/trackpad already).
  spreadsWrap.addEventListener('wheel', function(e) {
    if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
    e.preventDefault();
    spreadsWrap.scrollBy({left: e.deltaY});
  }, {passive: false});

  document.addEventListener('keydown', function(e) {
    if (!overlay.classList.contains('is-open')) return;
    if (e.key === 'Escape') {
      if (!article.hidden) { closeArticle(); } else { closeOverlay(); }
    } else if (e.key === 'ArrowLeft' && article.hidden) {
      step(-1);
    } else if (e.key === 'ArrowRight' && article.hidden) {
      step(1);
    }
  });
})();

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

  var poiModal = document.getElementById('magazine-poi-modal');
  var poiModalBody = document.getElementById('magazine-poi-modal-body');
  var poiModalBackdrop = document.getElementById('magazine-poi-modal-backdrop');
  var poiModalClose = document.getElementById('magazine-poi-modal-close');

  function spreads() {
    return Array.prototype.slice.call(spreadsWrap.querySelectorAll('[data-magazine-spread]'));
  }

  // Magazine mode is a standing preference, not a per-page state: every
  // page is a full server-rendered load (no SPA routing), so the only way
  // "stay in magazine view as I browse" survives navigation is to persist
  // it and re-open on arrival. This script only ever runs on pages where
  // the overlay exists (base.html only includes it when magazine_available
  // is true) — on a page without a magazine, the flag just stays parked
  // until the next page that has one.
  var MAG_MODE_KEY = 'w66-magazine-mode';

  function setMagazineMode(on) {
    try {
      if (on) localStorage.setItem(MAG_MODE_KEY, '1');
      else localStorage.removeItem(MAG_MODE_KEY);
    } catch (e) { /* localStorage unavailable (private mode, etc.) — degrade to per-page only */ }
    if (openBtn) openBtn.classList.toggle('is-active', on);
  }

  function magazineModeWanted() {
    try {
      return localStorage.getItem(MAG_MODE_KEY) === '1';
    } catch (e) {
      return false;
    }
  }

  // Jump straight to whichever spread represents where the reader currently
  // is (set server-side per page — see magazine_current_path in views.py),
  // instead of landing on an unrelated spread from the freshly-shuffled
  // deck. No smooth animation: it should read as "already there", not as a
  // swipe through everything in between.
  function jumpToCurrentSpread() {
    var path = overlay.getAttribute('data-current-path');
    if (!path) return;
    var match = spreadsWrap.querySelector('[data-magazine-spread][data-path="' + CSS.escape(path) + '"]');
    if (match) match.scrollIntoView({inline: 'start', block: 'nearest'});
  }

  function openOverlay() {
    overlay.classList.add('is-open');
    overlay.setAttribute('aria-hidden', 'false');
    docBody.classList.add('magazine-open');
    setMagazineMode(true);
    jumpToCurrentSpread();
  }

  function closeOverlay() {
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    docBody.classList.remove('magazine-open');
    setMagazineMode(false);
    closePoiModal();
  }

  // A quick peek at a POI without leaving the magazine. Clicking a pick
  // used to navigate to the POI's own full page — but with magazine mode
  // now a standing preference, that page just reopens the same magazine
  // overlay on top of it (usually showing the very same spread), so the
  // POI's actual content was never reachable. This fetches and shows the
  // same content in place instead, reusing api_page_content like the
  // article body itself does.
  function closePoiModal() {
    if (!poiModal) return;
    poiModal.classList.remove('is-open');
    poiModal.setAttribute('aria-hidden', 'true');
  }

  function openPoiModal(path, fallbackUrl) {
    if (!poiModal || !poiModalBody) {
      if (fallbackUrl) window.location.href = fallbackUrl;
      return;
    }
    poiModalBody.innerHTML = '<div class="magazine-poi-modal-loading"></div>';
    poiModal.classList.add('is-open');
    poiModal.setAttribute('aria-hidden', 'false');

    fetch('/api/page-content/' + path)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var hero = data.image_url
          ? '<div class="magazine-poi-modal-hero"><img src="' + data.image_url + '" alt="">'
            + '<div class="magazine-poi-modal-hero-veil"></div>'
            + '<div class="magazine-poi-modal-hero-title">' + (data.title || '') + '</div></div>'
          : '';
        poiModalBody.innerHTML = hero
          + '<div class="magazine-poi-modal-content">'
          + (hero ? '' : '<h2 class="magazine-poi-modal-title-plain">' + (data.title || '') + '</h2>')
          + (data.body_html || (data.snippet ? '<p>' + data.snippet + '</p>' : ''))
          + '<div class="magazine-poi-modal-footer"><a class="magazine-poi-modal-viewfull" href="' + data.url + '">View full page &rarr;</a></div>'
          + '</div>';
      })
      .catch(function() {
        poiModalBody.innerHTML = '<div class="magazine-poi-modal-content">'
          + '<p>Sorry, something went wrong loading this.</p>'
          + '<a class="magazine-poi-modal-viewfull" href="' + (fallbackUrl || '#') + '">View full page &rarr;</a>'
          + '</div>';
      });
  }

  // Middle-click / cmd-click / ctrl-click / shift-click should still open
  // the real page in a new tab, as any link would — only a plain left
  // click is intercepted into the modal.
  function isPlainClick(e) {
    return !(e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button === 1);
  }

  if (poiModalClose) poiModalClose.addEventListener('click', closePoiModal);
  if (poiModalBackdrop) poiModalBackdrop.addEventListener('click', closePoiModal);

  // One gesture = one step, guarded by the scroll's own completion rather
  // than a guessed cooldown length — a fixed timeout that's even slightly
  // shorter than the actual smooth-scroll animation lets a second wheel
  // event queue another step while the first is still animating, so it
  // overshoots by two spreads instead of one.
  var stepping = false;
  function clearStepping() { stepping = false; }
  spreadsWrap.addEventListener('scrollend', clearStepping);

  function step(dir) {
    if (stepping) return;
    stepping = true;
    spreadsWrap.scrollBy({left: dir * spreadsWrap.clientWidth, behavior: 'smooth'});
    // Safety net for browsers without `scrollend` (older Safari) or if a
    // scroll gets interrupted and never fires it.
    setTimeout(clearStepping, 900);
  }

  function shuffle() {
    var shuffled = spreads().sort(function() { return Math.random() - 0.5; });
    shuffled.forEach(function(el) { spreadsWrap.appendChild(el); });
    spreadsWrap.scrollTo({left: 0});
  }

  function newMapId() {
    return 'magazine-map-' + (mapIdCounter++);
  }

  // A deliberately different, more playful map than the rest of the site:
  // a colourful basemap (no API key needed — same free CARTO CDN the site
  // already relies on, just its "Voyager" style rather than the muted
  // greyscale used elsewhere) and big, chunky numbered pins instead of
  // small dots/labels.
  var MAG_TILE_URL = 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';

  var MAG_CATEGORY_CLASS = {'Restaurant': 'food', 'Bar': 'drink', 'Shopping': 'shop'};

  function magCategoryClass(category) {
    return MAG_CATEGORY_CLASS[category] || 'sight';
  }

  function magPinIcon(html, extraCls, size) {
    return L.divIcon({
      className: '',
      html: '<div class="mag-pin' + (extraCls ? ' ' + extraCls : '') + '">' + html + '</div>',
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    });
  }

  function magBaseMap(elementId, zoomControl) {
    var map = L.map(elementId, {
      zoomControl: !!zoomControl,
      attributionControl: false,
      scrollWheelZoom: false,
    });
    L.tileLayer(MAG_TILE_URL, {subdomains: 'abcd', maxZoom: 20}).addTo(map);
    return map;
  }

  // A locator box centred between a country's centroid and a specific
  // point within it, sized proportionally to the distance between them
  // (with a floor so even a very central city still reads as "zoomed out
  // to the country", not a tight crop). Not a real national boundary —
  // just enough geographic context for a decorative locator map.
  function countryLocatorBounds(countryLat, countryLng, lat, lng) {
    var latSpan = Math.max(Math.abs(lat - countryLat) * 2.6, 3.5);
    var lngSpan = Math.max(Math.abs(lng - countryLng) * 2.6, 4.5);
    var cLat = (countryLat + lat) / 2;
    var cLng = (countryLng + lng) / 2;
    return L.latLngBounds(
      [cLat - latSpan / 2, cLng - lngSpan / 2],
      [cLat + latSpan / 2, cLng + lngSpan / 2]
    );
  }

  function initMagazineLocatorMap(elementId, countryLat, countryLng, destName, lat, lng) {
    var map = magBaseMap(elementId, false);
    map.fitBounds(countryLocatorBounds(countryLat, countryLng, lat, lng));
    // No marker at the country's centroid — it isn't a place you'd click or
    // visit, so a pin there had no function. The zoomed-out basemap itself
    // (which carries country/region labels) plus the destination pin is
    // enough to read as "here, within this country."
    L.marker([lat, lng], {icon: magPinIcon('&#9733;', 'mag-pin--dest', 34)})
      .bindTooltip(destName, {direction: 'top', offset: [0, -14], permanent: true, className: 'mag-tip mag-tip--dest'})
      .addTo(map);
  }

  // The "country map" — woven into the article text itself, right after
  // the first paragraph, rather than bolted on at the end.
  function insertCountryMap(contentEl, data) {
    if (!data.country || typeof L === 'undefined' || typeof data.lat !== 'number') return;

    var wrap = document.createElement('div');
    wrap.className = 'magazine-country-map-wrap';
    var mapDiv = document.createElement('div');
    mapDiv.className = 'magazine-country-map';
    mapDiv.id = newMapId();
    var caption = document.createElement('div');
    caption.className = 'magazine-country-map-caption';
    caption.textContent = (data.title || 'This spot') + ' in ' + data.country.name;
    wrap.appendChild(mapDiv);
    wrap.appendChild(caption);

    var firstP = contentEl.querySelector('p');
    if (firstP && firstP.parentNode) {
      firstP.parentNode.insertBefore(wrap, firstP.nextSibling);
    } else {
      contentEl.insertBefore(wrap, contentEl.firstChild);
    }

    requestAnimationFrame(function() {
      initMagazineLocatorMap(mapDiv.id, data.country.lat, data.country.lng, data.title, data.lat, data.lng);
    });
  }

  function initMagazinePoiMap(elementId, destName, lat, lng, items, pinClassFn, onItemClick) {
    var map = magBaseMap(elementId, true);
    var group = L.featureGroup();
    L.marker([lat, lng], {icon: magPinIcon('&#9733;', 'mag-pin--dest', 34)})
      .bindTooltip(destName, {direction: 'top', offset: [0, -14], permanent: true, className: 'mag-tip mag-tip--dest'})
      .addTo(group);
    items.forEach(function(item, i) {
      if (typeof item.lat !== 'number' || typeof item.lng !== 'number') return;
      var mk = L.marker([item.lat, item.lng], {
        icon: magPinIcon(String(i + 1), 'mag-pin--' + pinClassFn(item), 30),
      });
      mk.bindTooltip(item.name || '', {direction: 'top', offset: [0, -12], className: 'mag-tip'});
      if (onItemClick) {
        mk.on('click', function() { onItemClick(item); });
      } else if (item.url) {
        mk.on('click', function() { window.location.href = item.url; });
      }
      mk.addTo(group);
    });
    group.addTo(map);
    map.fitBounds(group.getBounds().pad(0.3));
  }

  function setSectionHeading(poisWrap, subhead) {
    var subheadEl = poisWrap.querySelector('.magazine-article-subhead');
    if (!subheadEl) return;
    subheadEl.textContent = subhead || '';
    subheadEl.hidden = !subhead;
  }

  var MAG_POI_GROUPS = [
    {cat: 'sight', heading: 'Things to do'},
    {cat: 'food', heading: 'Where to eat'},
    {cat: 'drink', heading: 'Where to drink'},
    {cat: 'shop', heading: 'Shopping'},
  ];

  function renderPois(spread, data) {
    var pois = data.pois || [];
    var hasMap = typeof L !== 'undefined' && typeof data.lat === 'number';
    if (!pois.length && !hasMap) return;

    var poisWrap = spread.querySelector('.magazine-article-pois');
    var list = spread.querySelector('.magazine-article-poi-list');
    poisWrap.hidden = false;
    poisWrap.classList.remove('magazine-article-pois--cities');
    // Each category's own heading already says what it is — one more
    // generic label above them all would just repeat the same idea twice.
    setSectionHeading(poisWrap, null);

    // The single best pick overall leads as a full-width, colour-block
    // "cover story" — its own special look — and is left out of the
    // category lists below so it isn't shown twice. Sights, food, and
    // drink are never mixed into one list — each reads as its own short,
    // handpicked selection, side by side in columns, not one flat ranking.
    var featured = pois[0];
    var rest = pois.slice(1);

    if (featured) {
      var cat = magCategoryClass(featured.category);
      var hero = document.createElement('a');
      hero.href = featured.url;
      hero.className = 'magazine-pick-hero magazine-pick-hero--' + cat;
      var heroThumb = featured.image_url ? '<img src="' + featured.image_url + '" alt="" class="magazine-pick-hero-thumb">' : '';
      hero.innerHTML = '<span class="magazine-pick-hero-kicker">Don\'t miss &middot; ' + (featured.category || 'Sight') + '</span>'
        + '<span class="magazine-pick-hero-name">' + (featured.name || '') + '</span>'
        + (featured.snippet ? '<span class="magazine-pick-hero-snippet">' + featured.snippet + '</span>' : '')
        + heroThumb;
      hero.addEventListener('click', function(e) {
        if (!isPlainClick(e)) return;
        e.preventDefault();
        openPoiModal(featured.path, featured.url);
      });
      list.appendChild(hero);
    }

    var columns = document.createElement('div');
    columns.className = 'magazine-picks-columns';

    MAG_POI_GROUPS.forEach(function(group) {
      var items = rest.filter(function(p) { return magCategoryClass(p.category) === group.cat; });
      if (!items.length) return;

      var section = document.createElement('div');
      section.className = 'magazine-picks magazine-picks--' + group.cat;
      var heading = document.createElement('h3');
      heading.className = 'magazine-picks-heading';
      heading.textContent = group.heading;
      section.appendChild(heading);

      var ol = document.createElement('ol');
      ol.className = 'magazine-picks-list';
      items.forEach(function(poi, i) {
        var li = document.createElement('li');
        li.className = 'magazine-pick';
        var a = document.createElement('a');
        a.href = poi.url;
        a.className = 'magazine-pick-link';
        var thumb = poi.image_url ? '<img src="' + poi.image_url + '" alt="" class="magazine-pick-thumb">' : '';
        a.innerHTML = '<span class="magazine-pick-num">' + String(i + 1).padStart(2, '0') + '</span>'
          + thumb
          + '<span class="magazine-pick-body">'
          + '<span class="magazine-pick-name">' + (poi.name || '') + '</span>'
          + (poi.snippet ? '<span class="magazine-pick-snippet">' + poi.snippet + '</span>' : '')
          + '</span>';
        a.addEventListener('click', function(e) {
          if (!isPlainClick(e)) return;
          e.preventDefault();
          openPoiModal(poi.path, poi.url);
        });
        li.appendChild(a);
        ol.appendChild(li);
      });
      section.appendChild(ol);
      columns.appendChild(section);
    });

    if (columns.children.length) list.appendChild(columns);

    if (hasMap) {
      var mapWrap = document.createElement('div');
      mapWrap.className = 'magazine-poi-item--map';
      var mapDiv = document.createElement('div');
      mapDiv.className = 'magazine-poi-map';
      mapDiv.id = newMapId();
      mapWrap.appendChild(mapDiv);
      list.appendChild(mapWrap);
      requestAnimationFrame(function() {
        initMagazinePoiMap(mapDiv.id, data.title, data.lat, data.lng, pois,
          function(p) { return magCategoryClass(p.category); },
          function(p) { openPoiModal(p.path, p.url); });
      });
    }
  }

  // A page with no POIs of its own — a continent/country/region (POIs
  // live under cities) or a city with neighbourhoods (POIs live under
  // those) — shows the real places underneath it instead: image-led
  // cards (these are actual places with real photography, unlike POIs)
  // so it reads as an exciting "where to go next" rather than a dry index.
  function renderCities(spread, data) {
    var cities = data.cities || [];
    var hasMap = typeof L !== 'undefined' && typeof data.lat === 'number';
    if (!cities.length && !hasMap) return;

    var poisWrap = spread.querySelector('.magazine-article-pois');
    var list = spread.querySelector('.magazine-article-poi-list');
    poisWrap.hidden = false;
    poisWrap.classList.add('magazine-article-pois--cities');
    setSectionHeading(poisWrap, data.cities_heading || 'Recommended cities');

    cities.forEach(function(city, i) {
      var featured = i === 0;
      var li = document.createElement('li');
      li.className = 'magazine-city-item' + (featured ? ' magazine-city-item--featured' : '');
      var a = document.createElement('a');
      a.href = city.url;
      a.className = 'magazine-city-link';
      a.innerHTML = '<img src="' + city.image_url + '" alt="" class="magazine-city-img" loading="lazy">'
        + '<div class="magazine-city-veil"></div>'
        + '<div class="magazine-city-txt">'
        + '<span class="magazine-city-name">' + (city.name || '') + '</span>'
        + (city.snippet && featured ? '<span class="magazine-city-snippet">' + city.snippet + '</span>' : '')
        + '</div>';
      li.appendChild(a);
      list.appendChild(li);
    });

    if (hasMap) {
      var mapLi = document.createElement('li');
      mapLi.className = 'magazine-poi-item magazine-poi-item--map';
      var mapDiv = document.createElement('div');
      mapDiv.className = 'magazine-poi-map';
      mapDiv.id = newMapId();
      mapLi.appendChild(mapDiv);
      list.appendChild(mapLi);
      requestAnimationFrame(function() {
        initMagazinePoiMap(mapDiv.id, data.title, data.lat, data.lng, cities, function() { return 'city'; });
      });
    }
  }

  // The cover teaser is the article's own real opening paragraph (cropped
  // only visually, by CSS) whenever data-teaser-from-body is set — so the
  // fetched body would otherwise repeat it verbatim as its own first
  // paragraph. Drop that one paragraph; the article picks up exactly where
  // the cover left off instead of restarting itself.
  function dropLeadParagraphIfShown(spread, html) {
    if (spread.getAttribute('data-teaser-from-body') !== '1') return html;
    return html.replace(/^\s*<p>[\s\S]*?<\/p>/, '');
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
        contentEl.innerHTML = dropLeadParagraphIfShown(spread, data.body_html || '');
        insertCountryMap(contentEl, data);
        if (data.cities && data.cities.length) {
          renderCities(spread, data);
        } else {
          renderPois(spread, data);
        }
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

  if (openBtn) openBtn.addEventListener('click', function() {
    if (overlay.classList.contains('is-open')) closeOverlay();
    else openOverlay();
  });
  if (closeBtn) closeBtn.addEventListener('click', closeOverlay);
  if (shuffleBtn) shuffleBtn.addEventListener('click', shuffle);
  if (prevBtn) prevBtn.addEventListener('click', function() { step(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function() { step(1); });

  // Horizontal gestures (trackpad two-finger swipe, shift+wheel) move
  // between spreads. Plain vertical wheel is left alone so it scrolls the
  // active spread's own cover-to-article content instead of the strip.
  // A fast/long swipe fires dozens of wheel events with large deltas, so
  // following deltaX 1:1 felt wildly oversensitive (a single swipe could
  // blow past several spreads) — step() itself now guards against that.
  spreadsWrap.addEventListener('wheel', function(e) {
    if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
    e.preventDefault();
    if (Math.abs(e.deltaX) < 8) return;
    step(e.deltaX > 0 ? 1 : -1);
  }, {passive: false});

  document.addEventListener('keydown', function(e) {
    if (!overlay.classList.contains('is-open')) return;
    if (e.key === 'Escape') {
      if (poiModal && poiModal.classList.contains('is-open')) {
        closePoiModal();
      } else {
        closeOverlay();
      }
    } else if (e.key === 'ArrowLeft') {
      step(-1);
    } else if (e.key === 'ArrowRight') {
      step(1);
    }
  });

  // Re-enter magazine mode automatically on arrival if the reader left it
  // on elsewhere on the site, so it behaves like a standing setting rather
  // than something that resets on every navigation.
  if (magazineModeWanted()) {
    openOverlay();
  }
})();

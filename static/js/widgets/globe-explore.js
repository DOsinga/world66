(function(window, document) {
  window.World66Widgets = window.World66Widgets || {};

  function globeExplore(options) {

  options = options || {};
  var root = typeof options.root === 'string' ? document.querySelector(options.root) : options.root;
  if (!root) return null;
  var cities = options.cities || [];
  var dataId = options.dataId || root.getAttribute('data-cities-id');
  if (!cities.length && dataId) {
    var dataEl = document.getElementById(dataId);
    if (dataEl) cities = JSON.parse(dataEl.textContent);
  }
  if (!cities.length) return null;
  var mapEl = root.querySelector('[data-globe-map]');
  var mapWrap = root;
  var panel = root.querySelector('[data-globe-panel]');
  var modeBtn = root.querySelector('[data-globe-mode]');
  var fullscreenBtn = root.querySelector('[data-globe-fullscreen]');
  var embedBtn = root.querySelector('[data-globe-embed]');
  var embedDialog = root.querySelector('[data-globe-embed-dialog]');
  var embedCode = root.querySelector('[data-globe-embed-code]');
  var embedClose = root.querySelector('[data-globe-embed-close]');
  var embedCopy = root.querySelector('[data-globe-embed-copy]');
  var scale = Number(options.scale || root.getAttribute('data-scale') || 1);
  if (!mapEl || !panel) return null;
  var canvas = document.createElement('canvas');
  var ctx = canvas.getContext('2d');
  var preloadCache = {};
  var routeRunId = 0;
  var view = { lon: -17.4, lat: 14.7 };
  var countries = [];
  var activeCity = null;
  var routeLine = [];
  var isExploring = false;
  var dragState = null;
  var suppressNextClick = false;
  var dpr = window.devicePixelRatio || 1;
  mapEl.appendChild(canvas);

  function escapeHtml(value) {
    var div = document.createElement('div');
    div.textContent = value || '';
    return div.innerHTML;
  }

  function preloadImage(src, done) {
    if (!src || preloadCache[src]) {
      done();
      return;
    }
    var img = new Image();
    var finished = false;
    function finish() {
      if (finished) return;
      finished = true;
      preloadCache[src] = true;
      done();
    }
    img.onload = finish;
    img.onerror = finish;
    img.src = src;
  }

  function positionCard(city) {
    if (!mapWrap) return;
    if (mapWrap.clientWidth >= 760 || isMapFullscreen()) {
      var centerX = mapWrap.clientWidth / 2;
      var centerY = mapWrap.clientHeight / 3;
      var left = centerX + 48;
      if (isMapFullscreen() && mapWrap.clientWidth < 760) {
        left = Math.max(16, (mapWrap.clientWidth - panel.offsetWidth) / 2);
      }
      panel.style.left = Math.round(left) + 'px';
      panel.style.top = Math.round(Math.max(20, centerY - panel.offsetHeight / 2)) + 'px';
    } else {
      panel.style.left = Math.max(16, (mapWrap.clientWidth - panel.offsetWidth) / 2) + 'px';
      panel.style.top = Math.max(16, mapWrap.clientHeight - panel.offsetHeight - 74) + 'px';
    }
  }

  function openCard(city) {
    setActiveCity(city);
    var snippet = city.snippet ? '<p class="city-card-snippet">' + escapeHtml(city.snippet) + '</p>' : '';
    // Set non-active state + new content, then double-rAF to ensure the browser
    // commits opacity:0 before we add 'active' and start the fade-in transition.
    panel.className = 'w66-ge-card';
    panel.innerHTML =
      '<a href="' + encodeURI(city.url) + '" class="city-card-link" target="' + escapeHtml(options.linkTarget || '_top') + '" aria-label="Explore ' + escapeHtml(city.title) + '">' +
        '<div class="city-card-photo">' +
          '<img src="' + encodeURI(city.image) + '" alt="' + escapeHtml(city.title) + '" loading="eager">' +
          '<div class="city-card-photo-shade"></div>' +
          '<div class="city-card-title-block">' +
            '<div class="city-card-name">' + escapeHtml(city.title) + '</div>' +
            '<div class="city-card-country">' + escapeHtml(city.country || '') + '</div>' +
          '</div>' +
        '</div>' +
        '<div class="city-card-body">' + snippet + '</div>' +
	      '</a>';
    requestAnimationFrame(function() {
      positionCard(city);
      requestAnimationFrame(function() {
        panel.classList.add('active');
      });
    });
  }

  function closeCard() {
    panel.classList.remove('active');
    clearTravelLine();
  }

  function clearTravelLine() {
    routeRunId += 1;
    routeLine = [];
    drawGlobe();
  }

  function setActiveCity(city) {
    activeCity = city;
    drawGlobe();
  }

  function rotationFor(city) {
    return {
      lon: city.lng,
      lat: Math.max(-70, Math.min(70, city.lat))
    };
  }

  function setGlobeRotation(city, duration, done) {
    var target = rotationFor(city);
    var start = { lon: view.lon, lat: view.lat };
    var started = performance.now();
    var length = duration || 800;
    function step(now) {
      var t = Math.min(1, (now - started) / length);
      var ease = t * t * (3 - 2 * t);
      view = {
        lon: start.lon + (target.lon - start.lon) * ease,
        lat: start.lat + (target.lat - start.lat) * ease
      };
      drawGlobe();
      if (t < 1) {
        requestAnimationFrame(step);
      } else if (done) {
        done();
      }
    }
    requestAnimationFrame(step);
  }

  function enterExploreMode() {
    if (isExploring) return;
    isExploring = true;
    clearTimeout(cycleTimer);
    closeCard();
    mapEl.classList.add('is-exploring-globe');
    drawGlobe();
    if (modeBtn) modeBtn.textContent = 'Back to auto-play';
  }

  function exitExploreMode() {
    if (!isExploring) return;
    isExploring = false;
    closeCard();
    mapEl.classList.remove('is-exploring-globe');
    canvas.style.cursor = '';
    drawGlobe();
    if (modeBtn) modeBtn.textContent = 'Explore the globe';
    scheduleNext(1400);
  }

  if (options.mode === 'explore') {
    enterExploreMode();
  }

  if (modeBtn) {
    modeBtn.onclick = function() {
      if (isExploring) exitExploreMode(); else enterExploreMode();
    };
  }

  function fullscreenElement() {
    return document.fullscreenElement || document.webkitFullscreenElement;
  }

  function isMapFullscreen() {
    return fullscreenElement() === mapWrap;
  }

  function updateFullscreenButton() {
    if (!fullscreenBtn) return;
    fullscreenBtn.textContent = isMapFullscreen() ? 'Exit full screen' : 'Full screen';
    fullscreenBtn.setAttribute(
      'aria-label',
      isMapFullscreen() ? 'Exit globe full screen' : 'View globe full screen'
    );
  }

  function toggleFullscreen() {
    if (!mapWrap) return;
    if (isMapFullscreen()) {
      if (document.exitFullscreen) document.exitFullscreen();
      else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
      return;
    }
    if (mapWrap.requestFullscreen) mapWrap.requestFullscreen();
    else if (mapWrap.webkitRequestFullscreen) mapWrap.webkitRequestFullscreen();
  }

  if (fullscreenBtn) {
    if (!mapWrap.requestFullscreen && !mapWrap.webkitRequestFullscreen) {
      fullscreenBtn.hidden = true;
    } else {
      fullscreenBtn.addEventListener('click', toggleFullscreen);
      document.addEventListener('fullscreenchange', function() {
        updateFullscreenButton();
        resizeCanvas();
        if (activeCity) positionCard(activeCity);
      });
      document.addEventListener('webkitfullscreenchange', function() {
        updateFullscreenButton();
        resizeCanvas();
        if (activeCity) positionCard(activeCity);
      });
    }
  }

  function embedHtml() {
    var url = typeof options.embedUrl === 'function' ? options.embedUrl() : options.embedUrl;
    url = url || window.location.href;
    var height = options.embedHeight || root.getAttribute('data-embed-height') || root.offsetHeight || 500;
    return '<iframe src="' + escapeHtml(url) + '" width="100%" height="' + escapeHtml(String(height)) + '" style="border:0" loading="lazy" allow="fullscreen"></iframe>';
  }

  function openEmbedDialog() {
    if (!embedDialog || !embedCode) return;
    embedCode.value = embedHtml();
    embedDialog.hidden = false;
    embedCode.focus();
    embedCode.select();
  }

  if (embedBtn && embedDialog && embedCode) {
    embedBtn.addEventListener('click', openEmbedDialog);
    if (embedCopy) {
      embedCopy.addEventListener('click', function() {
        embedCode.focus();
        embedCode.select();
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(embedCode.value);
        } else {
          document.execCommand('copy');
        }
        embedCopy.textContent = 'Copied';
        setTimeout(function() { embedCopy.textContent = 'Copy code'; }, 1400);
      });
    }
    if (embedClose) embedClose.addEventListener('click', function() { embedDialog.hidden = true; });
    embedDialog.addEventListener('click', function(event) {
      if (event.target === embedDialog) embedDialog.hidden = true;
    });
    document.addEventListener('keydown', function(event) {
      if (event.key === 'Escape' && !embedDialog.hidden) embedDialog.hidden = true;
    });
  }

  function canvasPoint(event) {
    var rect = canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    };
  }

  function destinationAtPoint(x, y) {
    var best = null;
    cities.forEach(function(city) {
      var p = project(city.lng, city.lat);
      if (!p || !p.visible) return;
      var dx = p.x - x;
      var dy = p.y - y;
      var dist = Math.sqrt(dx * dx + dy * dy);
      if (dist <= 12 && (!best || dist < best.dist)) {
        best = { city: city, dist: dist };
      }
    });
    return best ? best.city : null;
  }

  function updateCanvasCursor(event) {
    if (!isExploring || dragState) {
      canvas.style.cursor = '';
      return;
    }
    var point = canvasPoint(event);
    canvas.style.cursor = destinationAtPoint(point.x, point.y) ? 'pointer' : 'grab';
  }

  canvas.addEventListener('pointerdown', function(event) {
    if (!isExploring) return;
    canvas.style.cursor = 'grabbing';
    dragState = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      lastX: event.clientX,
      lastY: event.clientY,
      moved: false
    };
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener('pointermove', function(event) {
    if (!dragState || dragState.pointerId !== event.pointerId) {
      updateCanvasCursor(event);
      return;
    }
    var dx = event.clientX - dragState.lastX;
    var dy = event.clientY - dragState.lastY;
    var totalDx = event.clientX - dragState.startX;
    var totalDy = event.clientY - dragState.startY;
    var metrics = globeMetrics();
    if (Math.sqrt(totalDx * totalDx + totalDy * totalDy) > 4) {
      dragState.moved = true;
      suppressNextClick = true;
    }
    view = {
      lon: view.lon - dx / metrics.radius * 70,
      lat: Math.max(-70, Math.min(70, view.lat + dy / metrics.radius * 70))
    };
    dragState.lastX = event.clientX;
    dragState.lastY = event.clientY;
    drawGlobe();
  });

  function endDrag(event) {
    if (!dragState || dragState.pointerId !== event.pointerId) return;
    canvas.releasePointerCapture(event.pointerId);
    dragState = null;
    updateCanvasCursor(event);
    setTimeout(function() { suppressNextClick = false; }, 0);
  }

  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);
  canvas.addEventListener('pointerleave', function() {
    if (!dragState) canvas.style.cursor = '';
  });

  canvas.addEventListener('click', function(event) {
    if (!isExploring) return;
    if (suppressNextClick) return;
    var point = canvasPoint(event);
    var city = destinationAtPoint(point.x, point.y);
    if (!city) return;
    setGlobeRotation(city, 420);
    openCard(city);
  });

  var cycleCities = cities.slice();
  // Shuffle
  for (var i = cycleCities.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var tmp = cycleCities[i]; cycleCities[i] = cycleCities[j]; cycleCities[j] = tmp;
  }
  // Start near Dakar (west Africa) — use Île de Gorée as surrogate if Dakar isn't in the set
  var startTitles = ['Dakar', 'Ile de Gorée', 'Île de Gorée'];
  for (var si = 0; si < startTitles.length; si++) {
    var found = false;
    for (var i = 0; i < cycleCities.length; i++) {
      if (cycleCities[i].title === startTitles[si]) {
        var tmp = cycleCities[0]; cycleCities[0] = cycleCities[i]; cycleCities[i] = tmp;
        found = true; break;
      }
    }
    if (found) break;
  }

  var cycleIdx = 0, cycleTimer = null, cycleStarted = false;
  var MIN_JUMP_M = 900000, MAX_JUMP_M = 5000000;
  var MAX_HEADING_JITTER = Math.PI / 9; // 20 degrees
  var prevLat = null, prevLng = null;
  var recentUrls = [];
  var RECENT_WINDOW = Math.min(36, Math.max(8, Math.floor(cycleCities.length / 12)));

  // Normalize longitude difference to [-180, 180] to handle the dateline correctly
  function dlng(from, to) { var d = to - from; while (d > 180) d -= 360; while (d < -180) d += 360; return d; }

  function rad(value) {
    return value * Math.PI / 180;
  }

  function distanceMeters(fromLat, fromLng, toLat, toLng) {
    var r = 6371000;
    var lat1 = fromLat * Math.PI / 180;
    var lat2 = toLat * Math.PI / 180;
    var dLat = (toLat - fromLat) * Math.PI / 180;
    var dLng = dlng(fromLng, toLng) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1) * Math.cos(lat2) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return r * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  function bearing(fromLat, fromLng, toLat, toLng) {
    var lat1 = fromLat * Math.PI / 180;
    var lat2 = toLat * Math.PI / 180;
    var dLng = dlng(fromLng, toLng) * Math.PI / 180;
    var y = Math.sin(dLng) * Math.cos(lat2);
    var x = Math.cos(lat1) * Math.sin(lat2) -
            Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
    return Math.atan2(y, x);
  }

  function angleDelta(a, b) {
    var d = b - a;
    while (d > Math.PI) d -= Math.PI * 2;
    while (d < -Math.PI) d += Math.PI * 2;
    return d;
  }

  var curLat = 14.7, curLng = -17.4; // start near Dakar

  function rememberCity(city) {
    if (!city || !city.url) return;
    recentUrls.push(city.url);
    while (recentUrls.length > RECENT_WINDOW) recentUrls.shift();
  }

  function isRecent(city) {
    return city && city.url && recentUrls.indexOf(city.url) !== -1;
  }

  var ROUTE_SEGMENT_METERS = 18000;
  var MIN_ROUTE_STEPS = 48;

  function routePoints(fromLat, fromLng, toLat, toLng, distance) {
    var points = [];
    var steps = Math.max(MIN_ROUTE_STEPS, Math.ceil(distance / ROUTE_SEGMENT_METERS));
    var lat1 = fromLat * Math.PI / 180;
    var lng1 = fromLng * Math.PI / 180;
    var lat2 = toLat * Math.PI / 180;
    var lng2 = (fromLng + dlng(fromLng, toLng)) * Math.PI / 180;
    var x1 = Math.cos(lat1) * Math.cos(lng1);
    var y1 = Math.cos(lat1) * Math.sin(lng1);
    var z1 = Math.sin(lat1);
    var x2 = Math.cos(lat2) * Math.cos(lng2);
    var y2 = Math.cos(lat2) * Math.sin(lng2);
    var z2 = Math.sin(lat2);
    var omega = Math.acos(Math.max(-1, Math.min(1, x1 * x2 + y1 * y2 + z1 * z2)));
    if (omega < 0.0001) return [[fromLat, fromLng], [toLat, toLng]];
    for (var i = 0; i <= steps; i++) {
      var t = i / steps;
      var a = Math.sin((1 - t) * omega) / Math.sin(omega);
      var b = Math.sin(t * omega) / Math.sin(omega);
      var x = a * x1 + b * x2;
      var y = a * y1 + b * y2;
      var z = a * z1 + b * z2;
      var lat = Math.atan2(z, Math.sqrt(x * x + y * y)) * 180 / Math.PI;
      var lng = Math.atan2(y, x) * 180 / Math.PI;
      points.push([lat, lng]);
    }
    return points;
  }

  function chooseRoutePoints(picked) {
    return routePoints(picked.fromLat, picked.fromLng, picked.city.lat, picked.city.lng, picked.dist);
  }

  function animateTravelLine(picked, done) {
    clearTravelLine();
    panel.classList.remove('active');
    var points = chooseRoutePoints(picked);
    var duration = Math.max(650, Math.min(1800, picked.dist / 2800));
    var runId = routeRunId;
    setActiveCity({ lat: picked.fromLat, lng: picked.fromLng });
    var started = performance.now();
    function frame(now) {
      if (runId !== routeRunId) return;
      var t = Math.min(1, (now - started) / duration);
      var ease = t * t * (3 - 2 * t);
      var end = Math.max(2, Math.ceil(points.length * t));
      routeLine = points.slice(0, end);
      view = {
        lon: picked.fromLng + dlng(picked.fromLng, picked.city.lng) * ease,
        lat: Math.max(-70, Math.min(70, picked.fromLat + (picked.city.lat - picked.fromLat) * ease))
      };
      drawGlobe();
      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        setActiveCity(picked.city);
        setTimeout(done, 120);
        setTimeout(clearTravelLine, 900);
      }
    }
    requestAnimationFrame(frame);
  }

  function pickNext() {
    var scored = [];
    for (var i = cycleIdx; i < cycleCities.length; i++) {
      var city = cycleCities[i];
      var d = distanceMeters(curLat, curLng, city.lat, city.lng);
      scored.push({ i: i, city: city, dist: d });
    }
    var fresh = scored.filter(function(s) { return !isRecent(s.city); });
    if (fresh.length) scored = fresh;
    var inRange = scored.filter(function(s) { return s.dist >= MIN_JUMP_M && s.dist <= MAX_JUMP_M; });
    if (!inRange.length) inRange = scored.filter(function(s) { return s.dist >= MIN_JUMP_M; });
    if (!inRange.length) inRange = scored;

    inRange.forEach(function(s) {
      var cosAngle = 0;
      if (prevLat !== null) {
        var jitter = (Math.random() * 2 - 1) * MAX_HEADING_JITTER;
        var previousBearing = bearing(prevLat, prevLng, curLat, curLng) + jitter;
        var candidateBearing = bearing(curLat, curLng, s.city.lat, s.city.lng);
        cosAngle = Math.cos(angleDelta(previousBearing, candidateBearing));
      }
      s.score = 1 - cosAngle;
    });

    inRange.sort(function(a, b) { return a.score - b.score; });
    var topN = inRange.slice(0, Math.min(3, inRange.length));
    var chosen = topN[Math.floor(Math.random() * topN.length)];
    var tmp = cycleCities[cycleIdx]; cycleCities[cycleIdx] = cycleCities[chosen.i]; cycleCities[chosen.i] = tmp;
    var fromLat = curLat, fromLng = curLng;
    prevLat = curLat; prevLng = curLng;
    curLat = chosen.city.lat; curLng = chosen.city.lng;
    var city = cycleCities[cycleIdx];
    cycleIdx = (cycleIdx + 1) % cycleCities.length;
    rememberCity(city);
    return { city: city, dist: chosen.dist, fromLat: fromLat, fromLng: fromLng };
  }

  function scheduleNext(delay) {
    clearTimeout(cycleTimer);
    cycleTimer = setTimeout(function() {
      if (!cycleCities.length) { scheduleNext(500); return; }
      var picked = pickNext();
      var imageReady = false;
      var routeReady = false;
      function maybeOpenCard() {
        if (!imageReady || !routeReady || isExploring) return;
        openCard(picked.city);
        scheduleNext(4300);
      }
      preloadImage(picked.city.image, function() {
        imageReady = true;
        maybeOpenCard();
      });
      animateTravelLine(picked, function() {
        if (isExploring) return;
        routeReady = true;
        maybeOpenCard();
      });
    }, delay || 0);
  }

  function showOpeningCard() {
    if (!cycleCities.length || isExploring) return;
    var index = Math.floor(Math.random() * cycleCities.length);
    var city = cycleCities[index];
    var tmp = cycleCities[0];
    cycleCities[0] = cycleCities[index];
    cycleCities[index] = tmp;
    cycleIdx = 1 % cycleCities.length;
    curLat = city.lat;
    curLng = city.lng;
    view = rotationFor(city);
    rememberCity(city);
    openCard(city);
  }

  function startCycle() {
    if (cycleStarted) return;
    cycleStarted = true;
    showOpeningCard();
    scheduleNext(3600);
  }

  function globeMetrics() {
    var width = mapEl.clientWidth;
    var height = mapEl.clientHeight;
    return {
      width: width,
      height: height,
      cx: width / 2,
      cy: width >= 760 ? height / 3 : height / 2,
      radius: (width >= 760 ? height * 0.88 : Math.min(width * 0.72, height * 0.84)) * scale
    };
  }

  function resizeCanvas() {
    dpr = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(mapEl.clientWidth * dpr));
    canvas.height = Math.max(1, Math.round(mapEl.clientHeight * dpr));
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawGlobe();
  }

  function project(lng, lat) {
    var metrics = globeMetrics();
    var latRad = rad(lat);
    var viewLat = rad(view.lat);
    var dLng = rad(dlng(view.lon, lng));
    var cosLat = Math.cos(latRad);
    var cosc = Math.sin(viewLat) * Math.sin(latRad) +
               Math.cos(viewLat) * cosLat * Math.cos(dLng);
    if (cosc < -0.03) return null;
    return {
      x: metrics.cx + metrics.radius * cosLat * Math.sin(dLng),
      y: metrics.cy - metrics.radius * (
        Math.cos(viewLat) * Math.sin(latRad) -
        Math.sin(viewLat) * cosLat * Math.cos(dLng)
      ),
      visible: cosc >= 0
    };
  }

  function drawSpherePath() {
    var metrics = globeMetrics();
    ctx.beginPath();
    ctx.arc(metrics.cx, metrics.cy, metrics.radius, 0, Math.PI * 2);
  }

  function drawLine(coords, closePath) {
    var started = false;
    coords.forEach(function(coord) {
      var p = project(coord[0], coord[1]);
      if (!p || !p.visible) {
        started = false;
        return;
      }
      if (!started) {
        ctx.moveTo(p.x, p.y);
        started = true;
      } else {
        ctx.lineTo(p.x, p.y);
      }
    });
    if (closePath && started) ctx.closePath();
  }

  function drawGeometry(geometry) {
    if (!geometry) return;
    if (geometry.type === 'Polygon') {
      geometry.coordinates.forEach(function(ring) { drawLine(ring, true); });
    } else if (geometry.type === 'MultiPolygon') {
      geometry.coordinates.forEach(function(poly) {
        poly.forEach(function(ring) { drawLine(ring, true); });
      });
    }
  }

  function drawGraticule() {
    ctx.save();
    drawSpherePath();
    ctx.clip();
    ctx.strokeStyle = 'rgba(120,94,72,0.11)';
    ctx.lineWidth = 0.7;
    for (var lng = -180; lng <= 180; lng += 30) {
      var meridian = [];
      for (var lat = -85; lat <= 85; lat += 4) meridian.push([lng, lat]);
      ctx.beginPath();
      drawLine(meridian, false);
      ctx.stroke();
    }
    for (var plat = -60; plat <= 60; plat += 20) {
      var parallel = [];
      for (var plng = -180; plng <= 180; plng += 4) parallel.push([plng, plat]);
      ctx.beginPath();
      drawLine(parallel, false);
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawDots() {
    function drawDot(city, radius, color, strokeWidth) {
      var p = project(city.lng, city.lat);
      if (!p || !p.visible) return;
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.lineWidth = strokeWidth;
      ctx.strokeStyle = '#fff';
      ctx.stroke();
    }
    if (isExploring) {
      cities.forEach(function(city) { drawDot(city, 4.4, 'rgba(184,83,43,0.78)', 1.2); });
    }
    if (activeCity) drawDot(activeCity, 7, '#b8532b', 2);
  }

  function drawRoute() {
    if (!routeLine.length) return;
    ctx.save();
    drawSpherePath();
    ctx.clip();
    ctx.beginPath();
    drawLine(routeLine.map(function(point) { return [point[1], point[0]]; }), false);
    ctx.strokeStyle = '#b8532b';
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.shadowColor = 'rgba(90,40,16,0.28)';
    ctx.shadowBlur = 3;
    ctx.stroke();
    ctx.restore();
  }

  function drawGlobe() {
    if (!ctx) return;
    var metrics = globeMetrics();
    ctx.clearRect(0, 0, metrics.width, metrics.height);

    drawSpherePath();
    ctx.fillStyle = '#d6e2e3';
    ctx.fill();
    ctx.strokeStyle = 'rgba(120,94,72,0.20)';
    ctx.lineWidth = 1;
    ctx.stroke();

    drawGraticule();

    ctx.save();
    drawSpherePath();
    ctx.clip();
    ctx.beginPath();
    countries.forEach(function(feature) { drawGeometry(feature.geometry); });
    ctx.fillStyle = '#f5f0e7';
    ctx.fill();
    ctx.strokeStyle = 'rgba(120,94,72,0.24)';
    ctx.lineWidth = 0.7;
    ctx.stroke();
    ctx.restore();

    drawRoute();
    drawDots();
  }

  fetch(options.countriesUrl || '/static/geo/countries.geo.json')
    .then(function(response) { return response.json(); })
    .then(function(data) { countries = data.features || []; })
    .catch(function() { countries = []; })
    .then(function() {
      resizeCanvas();
      if ('ResizeObserver' in window) {
        new ResizeObserver(resizeCanvas).observe(mapEl);
      } else {
        window.addEventListener('resize', resizeCanvas);
      }
      if ('IntersectionObserver' in window) {
        var obs = new IntersectionObserver(function(entries) {
          entries.forEach(function(entry) {
            if (entry.isIntersecting) {
              if (options.mode !== 'explore') startCycle();
              obs.disconnect();
            }
          });
        }, { threshold: 0.4 });
        obs.observe(mapEl);
      } else {
        if (options.mode !== 'explore') setTimeout(startCycle, 1500);
      }
    });
    return { enterExploreMode: enterExploreMode, exitExploreMode: exitExploreMode, resize: resizeCanvas };
  }

  window.World66Widgets.globeExplore = globeExplore;
})(window, document);

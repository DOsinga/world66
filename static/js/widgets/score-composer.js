(function(window, document) {
  window.World66Widgets = window.World66Widgets || {};

  function scoreComposer(options) {
    options = options || {};
    var root = typeof options.root === 'string' ? document.querySelector(options.root) : options.root;
    if (!root) return null;

    var svg = root.querySelector('[data-compose-map]');
    var list = root.querySelector('[data-compose-list]');
    var sliders = root.querySelector('[data-compose-sliders]');
    var dimensionSelect = root.querySelector('[data-compose-dimension]');
    var profileSelect = root.querySelector('[data-compose-profile]');
    var nameInput = root.querySelector('[data-compose-name]');
    var saveBtn = root.querySelector('[data-compose-save]');
    var resetBtn = root.querySelector('[data-compose-reset]');
    var summary = root.querySelector('[data-compose-summary]');
    var listSummary = root.querySelector('[data-compose-list-summary]');
    var heading = root.querySelector('[data-compose-heading]');
    var exportBox = root.querySelector('[data-compose-export]');
    var fullscreenBtn = root.querySelector('[data-compose-fullscreen]');
    var embedBtn = root.querySelector('[data-compose-embed]');
    var embedDialog = root.querySelector('[data-compose-embed-dialog]');
    var embedCode = root.querySelector('[data-compose-embed-code]');
    var embedClose = root.querySelector('[data-compose-embed-close]');
    var embedCopy = root.querySelector('[data-compose-embed-copy]');
    if (!svg || !list || !sliders || !dimensionSelect) return null;

    var storageKey = 'world66.scoreComposer.profiles';
    var dims = ['culture', 'nature', 'leisure', 'adventure'];
    var labels = {
      culture: 'Culture',
      nature: 'Nature',
      leisure: 'Leisure',
      adventure: 'Adventure'
    };
    var defaults = {};
    var state = {};
    var locations = [];
    var latentLabels = [];
    var markerLayer = null;
    var hoverCard = null;
    var worldViewBox = { x: 0, y: 0, width: 1000, height: 520 };
    var viewBox = { x: 0, y: 0, width: 1000, height: 520 };
    var dragStart = null;

    function escapeHtml(value) {
      var div = document.createElement('div');
      div.textContent = value == null ? '' : String(value);
      return div.innerHTML;
    }

    function clone(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function clampScore(value) {
      return Math.max(0, Math.min(10, value));
    }

    function sigmoid(value) {
      if (value < -40) return 0;
      if (value > 40) return 1;
      return 1 / (1 + Math.exp(-value));
    }

    function project(lng, lat) {
      return {
        x: (Number(lng) + 180) / 360 * 1000,
        y: (90 - Number(lat)) / 180 * 520
      };
    }

    function pathFromRing(ring) {
      var d = '';
      ring.forEach(function(point, index) {
        var p = project(point[0], point[1]);
        d += (index ? 'L' : 'M') + p.x.toFixed(2) + ' ' + p.y.toFixed(2);
      });
      return d + 'Z';
    }

    function geometryPath(geometry) {
      if (!geometry) return '';
      if (geometry.type === 'Polygon') return geometry.coordinates.map(pathFromRing).join('');
      if (geometry.type === 'MultiPolygon') {
        return geometry.coordinates.map(function(poly) {
          return poly.map(pathFromRing).join('');
        }).join('');
      }
      return '';
    }

    function drawBaseMap(geo) {
      svg.innerHTML = '';
      applyViewBox();
      var ocean = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      ocean.setAttribute('class', 'w66-se-ocean');
      ocean.setAttribute('x', '0');
      ocean.setAttribute('y', '0');
      ocean.setAttribute('width', '1000');
      ocean.setAttribute('height', '520');
      svg.appendChild(ocean);

      var graticule = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      graticule.setAttribute('class', 'w66-se-graticule');
      for (var lng = -120; lng <= 120; lng += 60) {
        var a = project(lng, -75);
        var b = project(lng, 80);
        var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', a.x);
        line.setAttribute('x2', b.x);
        line.setAttribute('y1', a.y);
        line.setAttribute('y2', b.y);
        graticule.appendChild(line);
      }
      for (var lat = -60; lat <= 60; lat += 30) {
        var c = project(-180, lat);
        var e = project(180, lat);
        var hline = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        hline.setAttribute('x1', c.x);
        hline.setAttribute('x2', e.x);
        hline.setAttribute('y1', c.y);
        hline.setAttribute('y2', e.y);
        graticule.appendChild(hline);
      }
      svg.appendChild(graticule);

      var land = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      land.setAttribute('class', 'w66-se-land');
      (geo.features || []).forEach(function(feature) {
        var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', geometryPath(feature.geometry));
        land.appendChild(path);
      });
      svg.appendChild(land);

      markerLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      markerLayer.setAttribute('class', 'w66-se-markers');
      svg.appendChild(markerLayer);
    }

    function clampViewBox(next) {
      var minWidth = 170;
      var aspect = worldViewBox.width / worldViewBox.height;
      var width = Math.min(worldViewBox.width, Math.max(minWidth, next.width));
      var height = width / aspect;
      var maxX = worldViewBox.width - width;
      var maxY = worldViewBox.height - height;
      return {
        x: Math.min(maxX, Math.max(0, next.x)),
        y: Math.min(maxY, Math.max(0, next.y)),
        width: width,
        height: height
      };
    }

    function applyViewBox() {
      svg.setAttribute('viewBox', [
        viewBox.x.toFixed(2),
        viewBox.y.toFixed(2),
        viewBox.width.toFixed(2),
        viewBox.height.toFixed(2)
      ].join(' '));
    }

    function zoomMap(factor, anchor) {
      anchor = anchor || {
        x: viewBox.x + viewBox.width / 2,
        y: viewBox.y + viewBox.height / 2
      };
      var width = viewBox.width * factor;
      var height = width / (worldViewBox.width / worldViewBox.height);
      viewBox = clampViewBox({
        x: anchor.x - (anchor.x - viewBox.x) * width / viewBox.width,
        y: anchor.y - (anchor.y - viewBox.y) * height / viewBox.height,
        width: width,
        height: height
      });
      applyViewBox();
      update();
    }

    function panMap(dx, dy) {
      viewBox = clampViewBox({
        x: viewBox.x + dx,
        y: viewBox.y + dy,
        width: viewBox.width,
        height: viewBox.height
      });
      applyViewBox();
      update();
    }

    function resetMap() {
      viewBox = { x: 0, y: 0, width: 1000, height: 520 };
      applyViewBox();
      update();
    }

    function svgPoint(event) {
      var rect = svg.getBoundingClientRect();
      return {
        x: viewBox.x + (event.clientX - rect.left) / rect.width * viewBox.width,
        y: viewBox.y + (event.clientY - rect.top) / rect.height * viewBox.height
      };
    }

    function isVisible(item) {
      var point = project(item.lng, item.lat);
      return point.x >= viewBox.x && point.x <= viewBox.x + viewBox.width &&
        point.y >= viewBox.y && point.y <= viewBox.y + viewBox.height;
    }

    function selectedDim() {
      return dimensionSelect.value || dims[0];
    }

    function composedScore(item, dim) {
      var config = state[dim];
      var value = config.bias;
      for (var i = 0; i < config.weights.length; i += 1) {
        value += item.hidden[i] * config.weights[i];
      }
      if (config.activation === 'linear_clamped') return clampScore(value);
      return sigmoid(value) * 10;
    }

    function rankedLocations() {
      var dim = selectedDim();
      return locations.map(function(item) {
        return { item: item, score: composedScore(item, dim) };
      }).sort(function(a, b) {
        return b.score - a.score;
      });
    }

    function visibleRankedLocations() {
      return rankedLocations().filter(function(row) { return isVisible(row.item); });
    }

    function topContributions(item, dim) {
      var config = state[dim];
      return config.weights.map(function(weight, index) {
        return {
          label: latentLabels[index] || ('Latent ' + (index + 1)),
          value: item.hidden[index] * weight
        };
      }).sort(function(a, b) {
        return Math.abs(b.value) - Math.abs(a.value);
      }).slice(0, 2);
    }

    function renderSliders() {
      var dim = selectedDim();
      var config = state[dim];
      if (heading) heading.textContent = labels[dim];
      sliders.innerHTML = config.weights.map(function(weight, index) {
        var id = 'latent-weight-' + index;
        return '<div class="w66-se-slider w66-sc-slider" data-compose-weight="' + index + '">' +
          '<label for="' + id + '">' +
            '<span>' + escapeHtml(latentLabels[index] || ('Latent ' + (index + 1))) + '</span>' +
            '<strong data-compose-weight-value>' + weight.toFixed(2) + '</strong>' +
          '</label>' +
          '<input id="' + id + '" type="range" min="-2" max="2" step="0.01" value="' + weight.toFixed(2) + '">' +
        '</div>';
      }).join('');
      sliders.querySelectorAll('input').forEach(function(input) {
        input.addEventListener('input', function() {
          var control = input.closest('[data-compose-weight]');
          var index = Number(control.getAttribute('data-compose-weight'));
          var value = Number(input.value);
          state[selectedDim()].weights[index] = value;
          control.querySelector('[data-compose-weight-value]').textContent = value.toFixed(2);
          update();
        });
      });
    }

    function renderList(top) {
      var dim = selectedDim();
      list.innerHTML = top.map(function(row, index) {
        var item = row.item;
        var contributions = topContributions(item, dim);
        return '<li>' +
          '<a href="' + encodeURI(item.url) + '" target="' + escapeHtml(options.linkTarget || '_top') + '">' +
            '<span class="w66-se-rank">' + (index + 1) + '</span>' +
            '<span class="w66-se-place">' +
              '<strong>' + escapeHtml(item.name) + '</strong>' +
              '<small>' + escapeHtml(item.parent) + '</small>' +
            '</span>' +
            '<span class="w66-se-score">' + row.score.toFixed(1) + '</span>' +
          '</a>' +
          '<span class="w66-se-components">' +
            contributions.map(function(part) {
              return '<span>' + escapeHtml(part.label) + ' ' + (part.value >= 0 ? '+' : '') + part.value.toFixed(2) + '</span>';
            }).join('') +
          '</span>' +
        '</li>';
      }).join('');
    }

    function removeHoverCard() {
      if (hoverCard && hoverCard.parentNode) hoverCard.parentNode.removeChild(hoverCard);
      hoverCard = null;
    }

    function showHoverCard(row, point) {
      removeHoverCard();
      var item = row.item;
      hoverCard = document.createElement('div');
      hoverCard.className = 'w66-se-hover';
      hoverCard.innerHTML =
        '<strong>' + escapeHtml(item.name) + '</strong>' +
        '<small>' + escapeHtml(item.parent) + '</small>' +
        '<span>' + escapeHtml(labels[selectedDim()]) + ' ' + row.score.toFixed(1) + '</span>';
      root.appendChild(hoverCard);
      var x = (point.x - viewBox.x) / viewBox.width * svg.clientWidth;
      var y = (point.y - viewBox.y) / viewBox.height * svg.clientHeight;
      hoverCard.style.left = Math.min(root.clientWidth - hoverCard.offsetWidth - 12, Math.max(12, x + 16)) + 'px';
      hoverCard.style.top = Math.min(root.clientHeight - hoverCard.offsetHeight - 12, Math.max(12, y + 16)) + 'px';
    }

    function renderMarkers(ranked) {
      if (!markerLayer) return;
      markerLayer.innerHTML = '';
      ranked.slice(0, 250).forEach(function(row, index) {
        var point = project(row.item.lng, row.item.lat);
        var link = document.createElementNS('http://www.w3.org/2000/svg', 'a');
        link.setAttribute('href', row.item.url);
        link.setAttribute('target', options.linkTarget || '_top');
        var circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', point.x);
        circle.setAttribute('cy', point.y);
        circle.setAttribute('r', index < 50 ? Math.max(3.5, 8 - index * 0.06) : 2.2);
        circle.setAttribute('class', index < 50 ? 'w66-se-marker is-top' : 'w66-se-marker');
        link.appendChild(circle);
        link.addEventListener('mouseenter', function() { showHoverCard(row, point); });
        link.addEventListener('mouseleave', removeHoverCard);
        markerLayer.appendChild(link);

        if (index < 20) {
          var label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          label.setAttribute('x', point.x);
          label.setAttribute('y', point.y + 3.5);
          label.setAttribute('class', 'w66-se-marker-label');
          label.textContent = index + 1;
          markerLayer.appendChild(label);
        }
      });
    }

    function exportState() {
      if (!exportBox) return;
      exportBox.value = JSON.stringify({
        name: nameInput ? nameInput.value : 'Working set',
        dimensions: state
      }, null, 2);
    }

    function update() {
      var ranked = visibleRankedLocations();
      var top = ranked.slice(0, 50);
      var dim = selectedDim();
      if (summary) summary.textContent = 'Example regression · bias ' + state[dim].bias.toFixed(2) + ' · 12 weights';
      if (listSummary) listSummary.textContent = labels[dim] + ' from examples · top ' + top.length + ' of ' + ranked.length + ' visible destinations';
      renderList(top);
      renderMarkers(ranked);
      exportState();
    }

    function readProfiles() {
      try {
        return JSON.parse(window.localStorage.getItem(storageKey) || '[]');
      } catch (error) {
        return [];
      }
    }

    function writeProfiles(profiles) {
      window.localStorage.setItem(storageKey, JSON.stringify(profiles));
    }

    function renderProfiles() {
      if (!profileSelect) return;
      var profiles = readProfiles();
      profileSelect.innerHTML = '<option value="">Model default</option>' + profiles.map(function(profile, index) {
        return '<option value="' + index + '">' + escapeHtml(profile.name || ('Profile ' + (index + 1))) + '</option>';
      }).join('');
    }

    function saveProfile() {
      var profiles = readProfiles();
      var name = (nameInput && nameInput.value.trim()) || 'Working set';
      var selected = profileSelect ? profileSelect.value : '';
      var profile = { name: name, dimensions: clone(state) };
      if (selected === '') profiles.push(profile);
      else profiles[Number(selected)] = profile;
      writeProfiles(profiles);
      renderProfiles();
      if (profileSelect) profileSelect.value = String(profiles.length - 1);
    }

    function loadProfile() {
      var selected = profileSelect ? profileSelect.value : '';
      if (selected === '') {
        state = clone(defaults);
        if (nameInput) nameInput.value = 'Working set';
      } else {
        var profile = readProfiles()[Number(selected)];
        if (profile && profile.dimensions) {
          state = clone(profile.dimensions);
          if (nameInput) nameInput.value = profile.name || 'Working set';
        }
      }
      renderSliders();
      update();
    }

    function resetDimension() {
      var dim = selectedDim();
      state[dim] = clone(defaults[dim]);
      renderSliders();
      update();
    }

    function fullscreenElement() {
      return document.fullscreenElement || document.webkitFullscreenElement;
    }

    function isFullscreen() {
      return fullscreenElement() === root;
    }

    function updateFullscreenButton() {
      if (!fullscreenBtn) return;
      fullscreenBtn.textContent = isFullscreen() ? 'Exit full screen' : 'Full screen';
    }

    function toggleFullscreen() {
      if (isFullscreen()) {
        if (document.exitFullscreen) document.exitFullscreen();
        else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
        return;
      }
      if (root.requestFullscreen) root.requestFullscreen();
      else if (root.webkitRequestFullscreen) root.webkitRequestFullscreen();
    }

    function embedHtml() {
      var url = options.embedUrl || window.location.href;
      var height = options.embedHeight || root.offsetHeight || 720;
      return '<iframe src="' + escapeHtml(url) + '" width="100%" height="' + escapeHtml(String(height)) + '" style="border:0" loading="lazy" allow="fullscreen"></iframe>';
    }

    function openEmbedDialog() {
      if (!embedDialog || !embedCode) return;
      embedCode.value = embedHtml();
      embedDialog.hidden = false;
      embedCode.focus();
      embedCode.select();
    }

    dimensionSelect.addEventListener('change', function() {
      renderSliders();
      update();
    });
    if (profileSelect) profileSelect.addEventListener('change', loadProfile);
    if (saveBtn) saveBtn.addEventListener('click', saveProfile);
    if (resetBtn) resetBtn.addEventListener('click', resetDimension);
    root.querySelectorAll('[data-map-zoom]').forEach(function(button) {
      button.addEventListener('click', function() {
        zoomMap(button.getAttribute('data-map-zoom') === 'in' ? 0.72 : 1.38);
      });
    });
    root.querySelectorAll('[data-map-pan]').forEach(function(button) {
      button.addEventListener('click', function() {
        var direction = button.getAttribute('data-map-pan');
        var stepX = viewBox.width * 0.28;
        var stepY = viewBox.height * 0.28;
        panMap(
          direction === 'left' ? -stepX : direction === 'right' ? stepX : 0,
          direction === 'up' ? -stepY : direction === 'down' ? stepY : 0
        );
      });
    });
    root.querySelectorAll('[data-map-reset]').forEach(function(button) {
      button.addEventListener('click', resetMap);
    });
    svg.addEventListener('wheel', function(event) {
      event.preventDefault();
      zoomMap(event.deltaY < 0 ? 0.84 : 1.19, svgPoint(event));
    }, { passive: false });
    svg.addEventListener('pointerdown', function(event) {
      dragStart = {
        clientX: event.clientX,
        clientY: event.clientY,
        viewBox: Object.assign({}, viewBox)
      };
      svg.classList.add('is-dragging');
      svg.setPointerCapture(event.pointerId);
    });
    svg.addEventListener('pointermove', function(event) {
      if (!dragStart) return;
      var rect = svg.getBoundingClientRect();
      var dx = (event.clientX - dragStart.clientX) / rect.width * dragStart.viewBox.width;
      var dy = (event.clientY - dragStart.clientY) / rect.height * dragStart.viewBox.height;
      viewBox = clampViewBox({
        x: dragStart.viewBox.x - dx,
        y: dragStart.viewBox.y - dy,
        width: dragStart.viewBox.width,
        height: dragStart.viewBox.height
      });
      applyViewBox();
      update();
    });
    svg.addEventListener('pointerup', function() {
      dragStart = null;
      svg.classList.remove('is-dragging');
    });
    svg.addEventListener('pointercancel', function() {
      dragStart = null;
      svg.classList.remove('is-dragging');
    });
    if (fullscreenBtn) {
      fullscreenBtn.addEventListener('click', toggleFullscreen);
      document.addEventListener('fullscreenchange', updateFullscreenButton);
      document.addEventListener('webkitfullscreenchange', updateFullscreenButton);
    }
    if (embedBtn) embedBtn.addEventListener('click', openEmbedDialog);
    if (embedClose) embedClose.addEventListener('click', function() { embedDialog.hidden = true; });
    if (embedDialog) {
      embedDialog.addEventListener('click', function(event) {
        if (event.target === embedDialog) embedDialog.hidden = true;
      });
    }
    if (embedCopy) {
      embedCopy.addEventListener('click', function() {
        embedCode.focus();
        embedCode.select();
        if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(embedCode.value);
        else document.execCommand('copy');
        embedCopy.textContent = 'Copied';
        setTimeout(function() { embedCopy.textContent = 'Copy code'; }, 1400);
      });
    }

    Promise.all([
      fetch(options.dataUrl || '/static/widgets/score-composer.json').then(function(response) { return response.json(); }),
      fetch(options.geoUrl || '/static/geo/countries.geo.json').then(function(response) { return response.json(); })
    ]).then(function(results) {
      defaults = clone(results[0].defaults || {});
      state = clone(defaults);
      locations = results[0].locations || [];
      latentLabels = results[0].latentLabels || [];
      renderProfiles();
      renderSliders();
      drawBaseMap(results[1]);
      update();
    }).catch(function() {
      if (summary) summary.textContent = 'Could not load hidden scores.';
    });

    return { update: update };
  }

  window.World66Widgets.scoreComposer = scoreComposer;
})(window, document);

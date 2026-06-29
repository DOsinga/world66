(function(window, document) {
  window.World66Widgets = window.World66Widgets || {};

  function scoringExplorer(options) {
    options = options || {};
    var root = typeof options.root === 'string' ? document.querySelector(options.root) : options.root;
    if (!root) return null;

    var svg = root.querySelector('[data-score-map]');
    var list = root.querySelector('[data-score-list]');
    var summary = root.querySelector('[data-score-summary]');
    var reset = root.querySelector('[data-score-reset]');
    var fullscreenBtn = root.querySelector('[data-score-fullscreen]');
    var embedBtn = root.querySelector('[data-score-embed]');
    var embedDialog = root.querySelector('[data-score-embed-dialog]');
    var embedCode = root.querySelector('[data-score-embed-code]');
    var embedClose = root.querySelector('[data-score-embed-close]');
    var embedCopy = root.querySelector('[data-score-embed-copy]');
    if (!svg || !list) return null;

    var dims = ['culture', 'nature', 'leisure', 'adventure'];
    var labels = {
      culture: 'Culture',
      nature: 'Nature',
      leisure: 'Leisure',
      adventure: 'Adventure'
    };
    var weights = { culture: 1, nature: 1, leisure: 1, adventure: 1 };
    var locations = [];
    var markerLayer = null;
    var hoverCard = null;

    function escapeHtml(value) {
      var div = document.createElement('div');
      div.textContent = value == null ? '' : String(value);
      return div.innerHTML;
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
      if (geometry.type === 'Polygon') {
        return geometry.coordinates.map(pathFromRing).join('');
      }
      if (geometry.type === 'MultiPolygon') {
        return geometry.coordinates.map(function(poly) {
          return poly.map(pathFromRing).join('');
        }).join('');
      }
      return '';
    }

    function drawBaseMap(geo) {
      svg.innerHTML = '';
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

    function weightedScore(item) {
      var total = 0;
      dims.forEach(function(dim) {
        total += weights[dim] * item[dim];
      });
      return total;
    }

    function sortedLocations() {
      return locations.map(function(item) {
        return { item: item, score: weightedScore(item) };
      }).sort(function(a, b) {
        return b.score - a.score;
      });
    }

    function strongestDims(item) {
      return dims.slice().sort(function(a, b) { return item[b] - item[a]; }).slice(0, 2);
    }

    function updateSummary(top) {
      if (!summary) return;
      var active = dims.filter(function(dim) { return weights[dim] > 0; })
        .map(function(dim) { return labels[dim] + ' ' + weights[dim].toFixed(1); });
      summary.textContent = (active.length ? active.join(' / ') : 'All weights are zero') +
        ' · ' + top.length + ' destinations';
    }

    function renderList(top) {
      list.innerHTML = top.map(function(row, index) {
        var item = row.item;
        var topDims = strongestDims(item);
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
            topDims.map(function(dim) {
              return '<span>' + labels[dim] + ' ' + item[dim].toFixed(1) + '</span>';
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
        '<span>Score ' + row.score.toFixed(1) + '</span>' +
        '<span>C/N/L/A ' + item.culture.toFixed(1) + ' / ' + item.nature.toFixed(1) + ' / ' + item.leisure.toFixed(1) + ' / ' + item.adventure.toFixed(1) + '</span>';
      root.appendChild(hoverCard);
      var x = point.x / 1000 * svg.clientWidth;
      var y = point.y / 520 * svg.clientHeight;
      hoverCard.style.left = Math.min(root.clientWidth - hoverCard.offsetWidth - 12, Math.max(12, x + 16)) + 'px';
      hoverCard.style.top = Math.min(root.clientHeight - hoverCard.offsetHeight - 12, Math.max(12, y + 16)) + 'px';
    }

    function renderMarkers(ranked) {
      if (!markerLayer) return;
      markerLayer.innerHTML = '';
      ranked.slice(0, 250).forEach(function(row, index) {
        var item = row.item;
        var point = project(item.lng, item.lat);
        var link = document.createElementNS('http://www.w3.org/2000/svg', 'a');
        link.setAttribute('href', item.url);
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

    function update() {
      root.querySelectorAll('[data-score-control]').forEach(function(control) {
        var dim = control.getAttribute('data-score-control');
        var input = control.querySelector('input');
        var value = control.querySelector('[data-score-value]');
        weights[dim] = Number(input.value);
        if (value) value.textContent = weights[dim].toFixed(1);
      });
      var ranked = sortedLocations();
      var top = ranked.slice(0, 50);
      updateSummary(top);
      renderList(top);
      renderMarkers(ranked);
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
      var height = options.embedHeight || root.offsetHeight || 640;
      return '<iframe src="' + escapeHtml(url) + '" width="100%" height="' + escapeHtml(String(height)) + '" style="border:0" loading="lazy" allow="fullscreen"></iframe>';
    }

    function openEmbedDialog() {
      if (!embedDialog || !embedCode) return;
      embedCode.value = embedHtml();
      embedDialog.hidden = false;
      embedCode.focus();
      embedCode.select();
    }

    root.querySelectorAll('[data-score-control] input').forEach(function(input) {
      input.addEventListener('input', update);
    });
    if (reset) {
      reset.addEventListener('click', function() {
        root.querySelectorAll('[data-score-control] input').forEach(function(input) {
          input.value = '1';
        });
        update();
      });
    }
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
      fetch(options.dataUrl || '/static/widgets/scoring-explorer.json').then(function(response) { return response.json(); }),
      fetch(options.geoUrl || '/static/geo/countries.geo.json').then(function(response) { return response.json(); })
    ]).then(function(results) {
      locations = results[0].locations || [];
      drawBaseMap(results[1]);
      update();
    }).catch(function() {
      if (summary) summary.textContent = 'Could not load scoring data.';
    });

    return { update: update };
  }

  window.World66Widgets.scoringExplorer = scoringExplorer;
})(window, document);

/* Score radar — five-axis pentagon chart of a location's dimension scores */
(function () {
  var LABELS = [
    ['city_culture', 'City Culture'],
    ['historic_culture', 'Historic Culture'],
    ['nature', 'Nature'],
    ['leisure', 'Leisure'],
    ['adventure', 'Adventure'],
  ];

  function axisPoint(cx, cy, radius, index, value) {
    var angle = -Math.PI / 2 + index * (2 * Math.PI / LABELS.length);
    var r = radius * (value / 10);
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    };
  }

  function svgEl(tag, attrs) {
    var el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (var key in attrs) {
      el.setAttribute(key, attrs[key]);
    }
    return el;
  }

  function initScoreRadar(elementId, scores) {
    var container = document.getElementById(elementId);
    if (!container) return;

    var size = 220;
    var cx = size / 2;
    var cy = size / 2;
    var radius = size / 2 - 44;

    var svg = svgEl('svg', {
      viewBox: '0 0 ' + size + ' ' + size,
      width: '100%',
      class: 'score-radar-svg',
    });

    // Grid rings at 2/4/6/8/10
    for (var ring = 2; ring <= 10; ring += 2) {
      var ringPoints = [];
      for (var i = 0; i < LABELS.length; i++) {
        var p = axisPoint(cx, cy, radius, i, ring);
        ringPoints.push(p.x + ',' + p.y);
      }
      svg.appendChild(svgEl('polygon', {
        points: ringPoints.join(' '),
        class: 'score-radar-grid',
      }));
    }

    // Axis lines + labels
    for (var a = 0; a < LABELS.length; a++) {
      var end = axisPoint(cx, cy, radius, a, 10);
      svg.appendChild(svgEl('line', {
        x1: cx, y1: cy, x2: end.x, y2: end.y,
        class: 'score-radar-axis',
      }));

      var labelPoint = axisPoint(cx, cy, radius + 14, a, 10);
      var text = svgEl('text', {
        x: labelPoint.x, y: labelPoint.y,
        class: 'score-radar-label',
        'text-anchor': labelPoint.x > cx + 2 ? 'start' : (labelPoint.x < cx - 2 ? 'end' : 'middle'),
      });
      text.textContent = LABELS[a][1];
      svg.appendChild(text);
    }

    // Filled polygon of the actual scores
    var scorePoints = [];
    for (var s = 0; s < LABELS.length; s++) {
      var value = scores[LABELS[s][0]] || 0;
      var p2 = axisPoint(cx, cy, radius, s, value);
      scorePoints.push(p2.x + ',' + p2.y);
    }
    svg.appendChild(svgEl('polygon', {
      points: scorePoints.join(' '),
      class: 'score-radar-shape',
    }));

    container.innerHTML = '';
    container.appendChild(svg);
  }

  window.initScoreRadar = initScoreRadar;
})();

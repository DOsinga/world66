(function(window, document) {
  window.World66Widgets = window.World66Widgets || {};

  function photoMap(options) {
    options = options || {};
    var root = typeof options.root === 'string' ? document.querySelector(options.root) : options.root;
    if (!root) return null;
    var map = root.querySelector('[data-photo-map]');
    var panel = root.querySelector('[data-photo-map-card]');
    var close = root.querySelector('[data-photo-map-close]');
    var fullscreenBtn = root.querySelector('[data-photo-map-fullscreen]');
    var embedBtn = root.querySelector('[data-photo-map-embed]');
    var embedDialog = root.querySelector('[data-photo-map-embed-dialog]');
    var embedCode = root.querySelector('[data-photo-map-embed-code]');
    var embedClose = root.querySelector('[data-photo-map-embed-close]');
    var embedCopy = root.querySelector('[data-photo-map-embed-copy]');
    if (!map || !panel) return null;

    function escapeHtml(value) {
      var div = document.createElement('div');
      div.textContent = value || '';
      return div.innerHTML;
    }

    var closeTimer = null;

    function positionCard(button) {
      var rootRect = root.getBoundingClientRect();
      var buttonRect = button.getBoundingClientRect();
      var gap = 12;
      var width = panel.offsetWidth;
      var height = panel.offsetHeight;
      var left = buttonRect.right - rootRect.left + gap;
      if (left + width > root.clientWidth - gap) {
        left = buttonRect.left - rootRect.left - width - gap;
      }
      if (left < gap) {
        left = Math.min(root.clientWidth - width - gap, buttonRect.left - rootRect.left);
      }
      var top = buttonRect.top - rootRect.top + buttonRect.height / 2 - height / 2;
      top = Math.max(gap, Math.min(root.clientHeight - height - gap, top));
      panel.style.left = Math.round(Math.max(gap, left)) + 'px';
      panel.style.top = Math.round(top) + 'px';
    }

    function openCard(tile, button) {
      clearTimeout(closeTimer);
      var snippet = tile.snippet ? '<p class="city-card-snippet">' + escapeHtml(tile.snippet) + '</p>' : '';
      panel.innerHTML =
        '<button class="w66-pm-card-close" data-photo-map-close type="button" aria-label="Close">&times;</button>' +
        '<a href="' + encodeURI(tile.url) + '" class="city-card-link" target="_top" aria-label="Explore ' + escapeHtml(tile.title) + '">' +
          '<div class="city-card-photo">' +
            '<img src="' + encodeURI(tile.image) + '" alt="' + escapeHtml(tile.title) + '" loading="eager">' +
            '<div class="city-card-photo-shade"></div>' +
            '<div class="city-card-title-block">' +
              '<div class="city-card-name">' + escapeHtml(tile.title) + '</div>' +
              '<div class="city-card-country">' + escapeHtml(tile.type || '') + '</div>' +
            '</div>' +
          '</div>' +
          '<div class="city-card-body">' + snippet + '</div>' +
        '</a>';
      panel.classList.add('active');
      requestAnimationFrame(function() { positionCard(button); });
      var closeButton = panel.querySelector('[data-photo-map-close]');
      if (closeButton) closeButton.addEventListener('click', function(event) {
        event.preventDefault();
        panel.classList.remove('active');
      });
    }

    function visit(tile) {
      var target = options.linkTarget || '_top';
      if (target === '_self') {
        window.location.href = tile.url;
      } else {
        window.open(tile.url, target);
      }
    }

    function closeCardSoon() {
      clearTimeout(closeTimer);
      closeTimer = setTimeout(function() {
        panel.classList.remove('active');
      }, 180);
    }

    panel.addEventListener('mouseenter', function() { clearTimeout(closeTimer); });
    panel.addEventListener('mouseleave', closeCardSoon);

    function sizeMap(data) {
      var rect = root.getBoundingClientRect();
      if (!rect.width || !rect.height) return;
      var aspect = data.cols / data.rows;
      var width = rect.width;
      var height = width / aspect;
      if (height > rect.height) {
        height = rect.height;
        width = height * aspect;
      }
      map.style.width = width + 'px';
      map.style.height = height + 'px';
    }

    function shapeTile(button, corners) {
      corners = corners || [];
      var radius = '18%';
      button.style.borderTopLeftRadius = corners.indexOf('tl') === -1 ? '0' : radius;
      button.style.borderTopRightRadius = corners.indexOf('tr') === -1 ? '0' : radius;
      button.style.borderBottomRightRadius = corners.indexOf('br') === -1 ? '0' : radius;
      button.style.borderBottomLeftRadius = corners.indexOf('bl') === -1 ? '0' : radius;
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
      fullscreenBtn.setAttribute(
        'aria-label',
        isFullscreen() ? 'Exit photo map full screen' : 'View photo map full screen'
      );
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
      var height = options.embedHeight || root.offsetHeight || 560;
      return '<iframe src="' + escapeHtml(url) + '" width="100%" height="' + escapeHtml(String(height)) + '" style="border:0" loading="lazy" allow="fullscreen"></iframe>';
    }

    function openEmbedDialog() {
      if (!embedDialog || !embedCode) return;
      embedCode.value = embedHtml();
      embedDialog.hidden = false;
      embedCode.focus();
      embedCode.select();
    }

    if (fullscreenBtn) {
      if (!root.requestFullscreen && !root.webkitRequestFullscreen) {
        fullscreenBtn.hidden = true;
      } else {
        fullscreenBtn.addEventListener('click', toggleFullscreen);
        document.addEventListener('fullscreenchange', updateFullscreenButton);
        document.addEventListener('webkitfullscreenchange', updateFullscreenButton);
      }
    }

    if (embedBtn && embedDialog && embedCode) {
      embedBtn.addEventListener('click', openEmbedDialog);
      if (embedClose) embedClose.addEventListener('click', function() { embedDialog.hidden = true; });
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
      embedDialog.addEventListener('click', function(event) {
        if (event.target === embedDialog) embedDialog.hidden = true;
      });
      document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && !embedDialog.hidden) embedDialog.hidden = true;
      });
    }

    fetch(options.metadataUrl || '/static/widgets/photo-map.json')
      .then(function(response) { return response.json(); })
      .then(function(data) {
        root.style.setProperty('--w66-pm-cols', data.cols);
        root.style.setProperty('--w66-pm-rows', data.rows);
        map.style.backgroundImage = 'url("' + (options.imageUrl || data.image) + '")';
        sizeMap(data);
        if ('ResizeObserver' in window) {
          new ResizeObserver(function() { sizeMap(data); }).observe(root);
        } else {
          window.addEventListener('resize', function() { sizeMap(data); });
        }
        data.tiles.forEach(function(tile) {
          var button = document.createElement('button');
          button.type = 'button';
          button.className = 'w66-pm-tile';
          button.style.left = (tile.x / data.cols * 100) + '%';
          button.style.top = (tile.y / data.rows * 100) + '%';
          button.style.width = (100 / data.cols) + '%';
          button.style.height = (100 / data.rows) + '%';
          shapeTile(button, tile.corners);
          button.setAttribute('aria-label', tile.title);
          button.addEventListener('click', function() { visit(tile); });
          button.addEventListener('mouseenter', function() { openCard(tile, button); });
          button.addEventListener('mouseleave', closeCardSoon);
          button.addEventListener('focus', function() { openCard(tile, button); });
          map.appendChild(button);
        });
      });

    if (close) {
      close.addEventListener('click', function() {
        panel.classList.remove('active');
      });
    }
  }

  window.World66Widgets.photoMap = photoMap;
})(window, document);

/* Map Explore — full-screen drill-down map experience */

function initExploreMap(opts) {
    var elementId  = opts.elementId;
    var basePath   = opts.basePath;
    var baseTitle  = opts.baseTitle;
    var parentTitle = opts.parentTitle;
    var parentUrl  = opts.parentUrl;
    var mode       = opts.mode;        // 'locations' | 'city'
    var initMarkers = opts.markers || [];

    // ---- State ----
    var state = {
        mode: mode,
        markers: initMarkers,
        parentMarkers: null,   // saved when drilling into a city
        parentBounds: null,
        parentTitle: parentTitle || null,
        parentUrl: parentUrl || null,
    };

    // ---- Map init ----
    var map = L.map(elementId, {
        zoomControl: true,
        attributionControl: false,
        scrollWheelZoom: true,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd', maxZoom: 19,
    }).addTo(map);

    L.control.attribution({ position: 'bottomright', prefix: false })
        .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>')
        .addTo(map);

    // ---- Marker layer ----
    var group = L.featureGroup().addTo(map);

    var _tip = L.DomUtil.create('div', 'map-name-tip', map.getContainer());
    _tip.style.cssText = 'position:absolute;z-index:9999;display:none;pointer-events:none';
    var _tipMarker = null;

    function _positionTip() {
        if (!_tipMarker) return;
        var pt = map.latLngToContainerPoint([_tipMarker.lat, _tipMarker.lng]);
        var sz = map.getSize();
        var w = _tip.offsetWidth, h = _tip.offsetHeight;
        var above = pt.y > h + 20;
        var top = above ? pt.y - h - 10 : pt.y + 14;
        var left = Math.max(6, Math.min(Math.round(pt.x - w / 2), sz.x - w - 6));
        _tip.style.top = top + 'px';
        _tip.style.left = left + 'px';
    }

    function _showTip(m) {
        if (m.snippet) {
            _tip.className = 'map-name-tip map-name-tip--rich';
            _tip.innerHTML = '<span class="map-tip-name">' + (m.name || '') + '</span>'
                + '<div class="map-tip-snippet">' + m.snippet + '</div>';
        } else {
            _tip.className = 'map-name-tip';
            _tip.innerHTML = m.name || '';
        }
        _tip.style.display = 'block';
        _tipMarker = m;
        _positionTip();
    }

    function _hideTip() { _tip.style.display = 'none'; _tipMarker = null; }
    map.on('movestart zoomstart', _hideTip);

    // ---- Deconfliction (same as world66map.js) ----
    function _deconflict(pool, maxCount) {
        var PAD = 4, PX_PER_CHAR = 7, LINE_H = 18;
        var placed = [], result = [];
        for (var i = 0; i < pool.length && result.length < maxCount; i++) {
            var m = pool[i];
            var pt = map.latLngToContainerPoint(L.latLng(m.lat, m.lng));
            var w = (m.name || '').length * PX_PER_CHAR + 8;
            var box = { x1: pt.x - w/2 - PAD, y1: pt.y - PAD,
                        x2: pt.x + w/2 + PAD, y2: pt.y + LINE_H + PAD };
            if (!placed.some(function(p) {
                return box.x2 > p.x1 && box.x1 < p.x2 && box.y2 > p.y1 && box.y1 < p.y2;
            })) { placed.push(box); result.push(m); }
        }
        return result;
    }

    // ---- Render markers ----
    function _renderMarkers(pool) {
        var bounds = map.getBounds();
        var inView = pool.filter(function(m) { return bounds.contains([m.lat, m.lng]); });
        inView.sort(function(a, b) {
            return ((b.highlight ? 1 : 0) - (a.highlight ? 1 : 0)) || ((b.score || 0) - (a.score || 0));
        });
        _hideTip();
        group.clearLayers();
        var named = inView.filter(function(m) { return !!m.name; });
        var labelled = _deconflict(named, 12);
        var labelSet = {};
        labelled.forEach(function(m) { labelSet[m.lat + ',' + m.lng] = true; });

        inView.forEach(function(m) {
            if (labelSet[m.lat + ',' + m.lng]) return;
            var dot = L.marker([m.lat, m.lng], {
                icon: L.divIcon({
                    className: 'map-label',
                    html: '<div class="map-dot-hit"><i class="map-dot' + (m.highlight ? ' map-dot--highlight' : ' map-dot--grey') + '"></i></div>',
                    iconSize: [0,0], iconAnchor: [0,0],
                }),
                zIndexOffset: -500,
            });
            dot.on('mouseover', function() { _showTip(m); });
            dot.on('mouseout', _hideTip);
            dot.on('click', function() { _onMarkerClick(m); });
            dot.addTo(group);
        });

        labelled.forEach(function(m) {
            var cls = m.highlight ? ' map-label--highlight' : '';
            var lbl = L.marker([m.lat, m.lng], {
                icon: L.divIcon({
                    className: 'map-label' + cls,
                    html: '<i class="map-dot' + (m.highlight ? ' map-dot--highlight' : '') + '"></i><span>' + (m.name || '') + '</span>',
                    iconSize: [0,0], iconAnchor: [0,0],
                }),
                zIndexOffset: 1000,
            });
            if (m.snippet) {
                lbl.on('mouseover', function() { _showTip(m); });
                lbl.on('mouseout', _hideTip);
            }
            lbl.on('click', function() { _onMarkerClick(m); });
            lbl.addTo(group);
        });
    }

    map.on('zoomend moveend', function() { _renderMarkers(state.markers); });

    // ---- Fit bounds helper ----
    function _trimmedBounds(mkrs) {
        if (mkrs.length < 6) return null;
        var lats = mkrs.map(function(m) { return m.lat; }).sort(function(a,b){return a-b;});
        var lngs = mkrs.map(function(m) { return m.lng; }).sort(function(a,b){return a-b;});
        var lo = Math.floor(mkrs.length * 0.1), hi = Math.ceil(mkrs.length * 0.9) - 1;
        return L.latLngBounds([lats[lo], lngs[lo]], [lats[hi], lngs[hi]]);
    }

    function _fitMarkers(mkrs) {
        if (mkrs.length === 0) return;
        if (mkrs.length === 1) { map.setView([mkrs[0].lat, mkrs[0].lng], 13); return; }
        var b = (_trimmedBounds(mkrs) || group.getBounds()).pad(0.15);
        if (b.isValid()) map.fitBounds(b, { animate: true, duration: 0.5 });
    }

    function _setMarkers(mkrs) {
        state.markers = mkrs;
        _renderMarkers(mkrs);
    }

    // ---- Drawer ----
    var drawer     = document.getElementById('explore-drawer');
    var drawerImg  = document.getElementById('explore-drawer-img');
    var drawerImgW = document.getElementById('explore-drawer-img-wrap');
    var drawerTitle = document.getElementById('explore-drawer-title');
    var drawerSnip  = document.getElementById('explore-drawer-snippet');
    var drawerTags  = document.getElementById('explore-drawer-tags');
    var drawerLink  = document.getElementById('explore-drawer-link');
    var drawerClose = document.getElementById('explore-drawer-close');

    function _openDrawer(m) {
        drawerTitle.textContent = m.name || '';
        drawerSnip.textContent  = m.snippet || '';
        drawerLink.href = m.url || '#';

        if (m.image_url) {
            drawerImg.src = m.image_url;
            drawerImg.alt = m.name || '';
            drawerImgW.style.display = '';
        } else {
            drawerImgW.style.display = 'none';
        }

        var tags = (m.tags || []).filter(function(t) {
            return !['sights','things_to_do','attractions','landmarks','museums'].includes(t);
        });
        drawerTags.innerHTML = tags.map(function(t) {
            return '<span class="explore-tag">' + t.replace(/_/g, ' ') + '</span>';
        }).join('');

        drawer.classList.add('is-open');
        drawer.setAttribute('aria-hidden', 'false');
    }

    function _closeDrawer() {
        drawer.classList.remove('is-open');
        drawer.setAttribute('aria-hidden', 'true');
    }

    if (drawerClose) drawerClose.addEventListener('click', _closeDrawer);
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') _closeDrawer();
    });

    // ---- Topbar controls ----
    var zoomOutBtn   = document.getElementById('explore-zoom-out');
    var zoomOutLabel = document.getElementById('explore-zoom-out-label');
    var topbarTitle  = document.getElementById('explore-topbar-title');

    function _showZoomOut(title) {
        if (zoomOutBtn) {
            zoomOutLabel.textContent = title;
            zoomOutBtn.style.display = '';
        }
    }

    function _hideZoomOut() {
        if (zoomOutBtn) zoomOutBtn.style.display = 'none';
    }

    // ---- City drill-down ----
    function _enterCity(m) {
        _closeDrawer();
        // Save current state so we can zoom back out
        state.parentMarkers = state.markers.slice();
        state.parentBounds  = map.getBounds();
        state.parentTitle   = baseTitle;
        state.mode          = 'loading';

        if (topbarTitle) topbarTitle.textContent = m.name || '';
        _showZoomOut(baseTitle);

        fetch('/api/explore/' + m.path)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                state.mode = data.mode;
                _setMarkers(data.markers);
                if (data.markers.length) {
                    // Build a group from new markers to fit bounds
                    var tmpGroup = L.featureGroup();
                    data.markers.forEach(function(mk) {
                        L.marker([mk.lat, mk.lng]).addTo(tmpGroup);
                    });
                    var b = (_trimmedBounds(data.markers) || tmpGroup.getBounds()).pad(0.2);
                    if (b.isValid()) map.fitBounds(b, { animate: true, duration: 0.5 });
                } else {
                    map.setView([m.lat, m.lng], 13, { animate: true });
                }
                _renderMarkers(state.markers);
            })
            .catch(function() {
                // Fallback: just zoom to the city location
                state.mode = 'city';
                state.markers = [];
                map.setView([m.lat, m.lng], 13, { animate: true });
            });
    }

    function _exitCity() {
        _closeDrawer();
        state.mode    = 'locations';
        state.markers = state.parentMarkers || initMarkers;
        state.parentMarkers = null;
        if (topbarTitle) topbarTitle.textContent = baseTitle;
        _hideZoomOut();
        _setMarkers(state.markers);
        if (state.parentBounds && state.parentBounds.isValid()) {
            map.fitBounds(state.parentBounds, { animate: true, duration: 0.5 });
        } else {
            _fitMarkers(state.markers);
        }
        state.parentBounds = null;
    }

    if (zoomOutBtn) zoomOutBtn.addEventListener('click', _exitCity);

    // ---- Click routing ----
    function _onMarkerClick(m) {
        if (state.mode === 'locations') {
            // Has a sub-path to drill into
            if (m.path) {
                _enterCity(m);
            } else {
                window.location.href = m.url;
            }
        } else {
            // City mode: show drawer
            _openDrawer(m);
        }
    }

    // ---- Initial render ----
    if (mode === 'locations' && state.parentTitle) {
        _showZoomOut(state.parentTitle);
    }

    (function() {
        var mkrs = initMarkers;
        if (mkrs.length) {
            var tmpGroup = L.featureGroup();
            mkrs.forEach(function(m) { L.marker([m.lat, m.lng]).addTo(tmpGroup); });
            if (tmpGroup.getBounds().isValid()) {
                var b = (_trimmedBounds(mkrs) || tmpGroup.getBounds()).pad(0.15);
                map.fitBounds(b, { animate: false });
            } else {
                map.setView([20, 0], 2);
            }
        } else {
            map.setView([20, 0], 2);
        }
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                map.invalidateSize();
                _renderMarkers(initMarkers);
            });
        });
    })();
}

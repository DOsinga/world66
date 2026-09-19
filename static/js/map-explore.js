/* Map Explore — full-screen drill-down map with side drawer */

function initExploreMap(opts) {
    var elementId    = opts.elementId;
    var basePath     = opts.basePath;
    var baseTitle    = opts.baseTitle;
    // parentPath: null = no parent; '' = world root (/explore); 'a/b' = explore path
    var parentPath   = opts.parentPath !== undefined ? opts.parentPath : null;
    var parentTitle  = opts.parentTitle  || '';
    var mode         = opts.mode;
    var initMarkers  = opts.markers || [];

    // ---- State ----
    var state = {
        mode: mode,            // 'locations' | 'city' | 'loading'
        markers: initMarkers,
        parentStack: [],       // [{markers, bounds, title, backLabel}] pushed on drill-in
        pendingDrillPath: null, // path to drill into when user clicks "Explore →"
    };

    // ---- Map ----
    var map = L.map(elementId, {
        zoomControl: true,
        attributionControl: false,
        scrollWheelZoom: true,
    });

    var attribution = _addBaseTiles(map);

    L.control.attribution({ position: 'bottomright', prefix: false })
        .addAttribution(attribution)
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
        _tip.style.top = top + 'px'; _tip.style.left = left + 'px';
    }
    function _showTip(m) {
        _tip.className = m.snippet ? 'map-name-tip map-name-tip--rich' : 'map-name-tip';
        _tip.innerHTML = m.snippet
            ? '<span class="map-tip-name">' + (m.name||'') + '</span><div class="map-tip-snippet">' + m.snippet + '</div>'
            : (m.name || '');
        _tip.style.display = 'block'; _tipMarker = m; _positionTip();
    }
    function _hideTip() { _tip.style.display = 'none'; _tipMarker = null; }
    map.on('movestart zoomstart', _hideTip);

    // ---- Deconfliction ----
    function _deconflict(pool, maxCount) {
        var PAD=2, PPC=7, LH=18, placed=[], result=[];
        for (var i=0; i<pool.length && result.length<maxCount; i++) {
            var m=pool[i], pt=map.latLngToContainerPoint(L.latLng(m.lat,m.lng));
            var w=(m.name||'').length*PPC+8;
            var box={x1:pt.x-w/2-PAD,y1:pt.y-PAD,x2:pt.x+w/2+PAD,y2:pt.y+LH+PAD};
            if (!placed.some(function(p){return box.x2>p.x1&&box.x1<p.x2&&box.y2>p.y1&&box.y1<p.y2;}))
                { placed.push(box); result.push(m); }
        }
        return result;
    }

    var CURBSIDE_ZOOM = 15;   // show curbside POIs only at this zoom or above

    function _renderMarkers(pool) {
        var zoom   = map.getZoom();
        var bounds = map.getBounds();
        var inView = pool.filter(function(m) {
            if (!bounds.contains([m.lat, m.lng])) return false;
            if (m.curbside && zoom < CURBSIDE_ZOOM) return false;
            return true;
        });
        // Primaries first, then secondaries, curbside last; within each tier sort by score
        inView.sort(function(a, b) {
            var ta = a.curbside ? 0 : (a.highlight ? 2 : 1);
            var tb = b.curbside ? 0 : (b.highlight ? 2 : 1);
            return (tb - ta) || ((b.score||0) - (a.score||0));
        });
        _hideTip(); group.clearLayers();

        // Only non-curbside markers compete for labels
        var labelPool = inView.filter(function(m){ return !m.curbside && !!m.name; });
        var labelled  = _deconflict(labelPool, 30);
        var lblSet    = {};
        labelled.forEach(function(m){ lblSet[m.lat+','+m.lng] = true; });

        inView.forEach(function(m) {
            if (lblSet[m.lat+','+m.lng]) return;
            var dotCls = m.curbside ? ' map-dot--curbside'
                       : m.highlight ? ' map-dot--highlight' : ' map-dot--grey';
            var dot = L.marker([m.lat, m.lng], {
                icon: L.divIcon({className: 'map-label',
                    html: '<div class="map-dot-hit"><i class="map-dot' + dotCls + '"></i></div>',
                    iconSize:[0,0], iconAnchor:[0,0]}), zIndexOffset: m.curbside ? -1000 : -500});
            dot.on('mouseover', function(){ _showTip(m); }).on('mouseout', _hideTip)
               .on('click', function(){ _onMarkerClick(m); });
            dot.addTo(group);
        });
        labelled.forEach(function(m) {
            var cls = m.highlight ? ' map-label--highlight' : '';
            var lbl = L.marker([m.lat, m.lng], {
                icon: L.divIcon({className: 'map-label' + cls,
                    html: '<i class="map-dot' + (m.highlight ? ' map-dot--highlight' : '') + '"></i><span>' + (m.name||'') + '</span>',
                    iconSize:[0,0], iconAnchor:[0,0]}), zIndexOffset: 1000});
            if (m.snippet) lbl.on('mouseover', function(){ _showTip(m); }).on('mouseout', _hideTip);
            lbl.on('click', function(){ _onMarkerClick(m); });
            lbl.addTo(group);
        });
    }
    map.on('zoomend moveend', function(){_renderMarkers(state.markers);});

    function _trimmedBounds(mkrs) {
        if (mkrs.length<6) return null;
        var lats=mkrs.map(function(m){return m.lat;}).sort(function(a,b){return a-b;});
        var lngs=mkrs.map(function(m){return m.lng;}).sort(function(a,b){return a-b;});
        var lo=Math.floor(mkrs.length*0.1),hi=Math.ceil(mkrs.length*0.9)-1;
        return L.latLngBounds([lats[lo],lngs[lo]],[lats[hi],lngs[hi]]);
    }
    function _boundsFromMarkers(mkrs) {
        var g=L.featureGroup();
        mkrs.forEach(function(m){L.marker([m.lat,m.lng]).addTo(g);});
        return g.getBounds();
    }
    function _fitMarkers(mkrs, animate) {
        if (!mkrs.length) return;
        if (mkrs.length===1) { map.setView([mkrs[0].lat,mkrs[0].lng],13,{animate:!!animate}); return; }
        var b=(_trimmedBounds(mkrs)||_boundsFromMarkers(mkrs)).pad(0.15);
        if (b.isValid()) map.fitBounds(b,{animate:!!animate,duration:0.5});
    }

    // ---- Drawer ----
    var drawer      = document.getElementById('explore-drawer');
    var drawerImgW  = document.getElementById('explore-drawer-img-wrap');
    var drawerImg   = document.getElementById('explore-drawer-img');
    var drawerTitle = document.getElementById('explore-drawer-title');
    var drawerCont  = document.getElementById('explore-drawer-content');
    var drawerLink  = document.getElementById('explore-drawer-link');
    var drawerDrill = document.getElementById('explore-drawer-drill');
    var drawerClose = document.getElementById('explore-drawer-close');
    var body        = document.body;

    function _openDrawer(m) {
        // Show immediately with what we already know
        drawerTitle.textContent = m.name || '';
        drawerLink.href = m.url || '#';
        drawerCont.innerHTML = '';
        drawerCont.classList.add('is-loading');

        if (m.image_url) {
            drawerImg.src = m.image_url;
            drawerImg.alt = m.name || '';
            drawerImgW.classList.remove('no-image');
        } else {
            drawerImgW.classList.add('no-image');
        }

        // "Explore →" button only in locations mode (drilling into a city)
        if (drawerDrill) {
            if (state.mode === 'locations' && m.path) {
                state.pendingDrillPath = m.path;
                state.pendingDrillMarker = m;
                drawerDrill.style.display = '';
            } else {
                state.pendingDrillPath = null;
                drawerDrill.style.display = 'none';
            }
        }

        drawer.classList.add('is-open');
        drawer.setAttribute('aria-hidden', 'false');
        body.classList.add('drawer-open');

        // Fetch real content
        fetch('/api/page-content/' + m.path)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                drawerCont.classList.remove('is-loading');
                drawerCont.innerHTML = data.body_html || '';
                // Update image if we didn't already have one
                if (!m.image_url && data.image_url) {
                    drawerImg.src = data.image_url;
                    drawerImg.alt = data.title || '';
                    drawerImgW.classList.remove('no-image');
                }
            })
            .catch(function() {
                drawerCont.classList.remove('is-loading');
                drawerCont.textContent = m.snippet || '';
            });
    }

    function _closeDrawer() {
        drawer.classList.remove('is-open');
        drawer.setAttribute('aria-hidden', 'true');
        body.classList.remove('drawer-open');
        state.pendingDrillPath = null;
        if (drawerDrill) drawerDrill.style.display = 'none';
        // Refit map after drawer closes (map pane width changed)
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                map.invalidateSize();
            });
        });
    }

    if (drawerClose) drawerClose.addEventListener('click', _closeDrawer);
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') _closeDrawer();
    });

    // ---- Topbar controls ----
    var zoomOutBtn   = document.getElementById('explore-zoom-out');
    var zoomOutLabel = document.getElementById('explore-zoom-out-label');
    var topbarTitle  = document.getElementById('explore-topbar-title');

    function _setTopTitle(t) { if (topbarTitle) topbarTitle.textContent = t; }
    function _showZoomOut(t) { if (zoomOutBtn) { zoomOutLabel.textContent = t; zoomOutBtn.style.display = ''; } }
    function _hideZoomOut() { if (zoomOutBtn) zoomOutBtn.style.display = 'none'; }

    // ---- Drill into a city/location ----
    function _drillInto(m) {
        var leavingTitle    = topbarTitle ? topbarTitle.textContent : baseTitle;
        var leavingBackLabel = (zoomOutBtn && zoomOutBtn.style.display !== 'none')
            ? (zoomOutLabel ? zoomOutLabel.textContent : null) : null;
        state.parentStack.push({
            markers:   state.markers.slice(),
            bounds:    map.getBounds(),
            title:     leavingTitle,
            backLabel: leavingBackLabel,   // back-button text at the level we're leaving
        });
        state.mode = 'loading';

        _setTopTitle(m.name || '');
        _showZoomOut(leavingTitle);
        _closeDrawer();

        fetch('/api/explore/' + m.path)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                state.mode    = data.mode;
                state.markers = data.markers || [];
                _renderMarkers(state.markers);
                // Invalidate first so fitBounds uses the correct (post-drawer-close) dimensions
                map.invalidateSize();
                if (state.markers.length) {
                    var b = (_trimmedBounds(state.markers) || _boundsFromMarkers(state.markers)).pad(0.2);
                    if (b.isValid()) map.fitBounds(b, {animate:true, duration:0.6});
                } else {
                    map.setView([m.lat, m.lng], 13, {animate:true});
                }
            })
            .catch(function() {
                state.mode = 'city'; state.markers = [];
                map.setView([m.lat, m.lng], 13, {animate:true});
            });
    }

    function _exitCity() {
        _closeDrawer();
        if (state.parentStack.length) {
            // Drilled in via JS — pop the stack and zoom back out
            var parent = state.parentStack.pop();
            state.mode    = 'locations';
            state.markers = parent.markers;
            _setTopTitle(parent.title || baseTitle);
            // Restore the back button that was visible at the level we're returning to
            if (parent.backLabel !== null) {
                _showZoomOut(parent.backLabel);
            } else if (parentPath !== null && state.parentStack.length === 0) {
                // Returned to the initial page level — show page-level parent if any
                _showZoomOut(parentTitle || parent.title || baseTitle);
            } else {
                _hideZoomOut();
            }
            _renderMarkers(state.markers);
            var b = parent.bounds;
            if (b && b.isValid()) {
                map.fitBounds(b, {animate:true, duration:0.5});
            } else {
                _fitMarkers(state.markers, true);
            }
            requestAnimationFrame(function() { requestAnimationFrame(function() { map.invalidateSize(); }); });
        } else if (parentPath !== null) {
            // Directly-loaded page — navigate to parent explore page
            // parentPath '' = world root, otherwise a content path
            window.location.href = parentPath === '' ? '/explore' : '/explore/' + parentPath;
        }
    }

    if (zoomOutBtn) zoomOutBtn.addEventListener('click', _exitCity);

    // Show back button on load if the page has a page-level parent
    // (parentPath null = no parent; parentPath '' = world root; parentPath 'a/b' = explore path)
    if (parentPath !== null && parentTitle) {
        _showZoomOut(parentTitle);
    }

    // "Explore →" drills into the city whose drawer is open
    if (drawerDrill) {
        drawerDrill.addEventListener('click', function() {
            if (state.pendingDrillPath && state.pendingDrillMarker) {
                _drillInto(state.pendingDrillMarker);
            }
        });
    }

    // ---- Marker click ----
    function _onMarkerClick(m) {
        if (state.mode === 'loading') return;
        _openDrawer(m);
    }

    // ---- Initial render ----
    (function() {
        if (initMarkers.length) {
            var b = (_trimmedBounds(initMarkers) || _boundsFromMarkers(initMarkers)).pad(0.15);
            if (b.isValid()) map.fitBounds(b, {animate:false});
            else map.setView([20,0],2);
        } else {
            map.setView([20,0],2);
        }
        requestAnimationFrame(function() { requestAnimationFrame(function() {
            map.invalidateSize();
            _renderMarkers(initMarkers);
        }); });
    })();
}

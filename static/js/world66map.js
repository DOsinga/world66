/* World66 Map — Leaflet-based maps for the travel guide */

const W66_RED = '#b8532b';
const W66_RED_HOVER = '#c96035';
const W66_FILL = '#e8c4b0';
const W66_FILL_HOVER = '#f0d4c0';

/* ---- Home page: clickable continent map ---- */

function initContinentMap(elementId, w66continents) {
    const map = L.map(elementId, {
        zoomControl: false,
        attributionControl: false,
        scrollWheelZoom: false,
        dragging: false,
        doubleClickZoom: false,
        zoomSnap: 0.01,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
        maxZoom: 4,
        noWrap: true,
    }).addTo(map);

    // Label positions keyed by our slugs
    const LABEL_POS = {
        "africa":                     [  2,  22],
        "asia":                       [ 45,  90],
        "europe":                     [ 54,  14],
        "northamerica":               [ 48,-100],
        "australiaandpacific":        [-28, 134],
        "southamerica":               [-14, -58],
        "centralamericathecaribbean": [ 16, -78],
    };

    // Fill width exactly so no grey side bars; height crops the poles naturally.
    // Centre at +18° so the inhabited world is centred and Antarctica stays out.
    function _fitWorld() {
        const w = map.getContainer().offsetWidth;
        if (w > 0) {
            const zoom = Math.log2(w / 256);
            map.setView([18, 0], zoom, {animate: false});
        }
    }
    map.setView([18, 0], 1, {animate: false}); // initial view
    requestAnimationFrame(function() { requestAnimationFrame(_fitWorld); });

    // Long names that need a manual line break on the map
    const LABEL_BREAKS = {
        "australiaandpacific": "Australia, Pacific<br>& Antarctica",
    };

    // Typographic continent labels — no GeoJSON shapes
    w66continents.forEach(function(c) {
        const pos = LABEL_POS[c.slug];
        if (!pos) return;
        const labelHtml = LABEL_BREAKS[c.slug] || c.title;
        L.marker(pos, {
            icon: L.divIcon({
                className: 'continent-label',
                html: '<a href="' + c.url + '">' + labelHtml + '</a>',
                iconSize: [0, 0],
                iconAnchor: [0, 0],
            }),
        }).addTo(map);
    });

    L.control.attribution({position: 'bottomright', prefix: false})
        .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>')
        .addTo(map);

    return map;
}


/* ---- Country map: clickable countries within a continent ---- */

function initCountryMap(elementId, continentSlug, bounds) {
    const map = L.map(elementId, {
        zoomControl: true,
        attributionControl: false,
        scrollWheelZoom: true,
    });

    _addSplitTiles(map);

    if (bounds) {
        map.fitBounds(bounds);
    }

    const STYLE_DEFAULT = { fillColor: '#8faab8', fillOpacity: 0.18, color: '#6a8fa8', weight: 1, opacity: 0.55 };
    const STYLE_HOVER   = { fillOpacity: 0.42, weight: 1.5, opacity: 0.85 };

    fetch('/static/geo/countries.geo.json')
        .then(r => r.json())
        .then(data => {
            data.features = data.features.filter(f => {
                const slug = COUNTRY_SLUGS[f.properties.name];
                return slug && COUNTRY_CONTINENTS[slug] === continentSlug;
            });

            if (!bounds && data.features.length > 0) {
                map.fitBounds(L.geoJSON(data).getBounds().pad(0.1));
            }

            L.geoJSON(data, {
                style: STYLE_DEFAULT,
                onEachFeature: function(feature, layer) {
                    const name = feature.properties.name;
                    const slug = COUNTRY_SLUGS[name];
                    if (!slug) return;
                    layer.bindTooltip(name, { className: 'country-tooltip', sticky: true });
                    layer.on('mouseover', function() { layer.setStyle(STYLE_HOVER); });
                    layer.on('mouseout',  function() { layer.setStyle(STYLE_DEFAULT); });
                    layer.on('click',     function() { window.location.href = '/' + continentSlug + '/' + slug; });
                },
            }).addTo(map);
        });

    L.control.attribution({position: 'bottomright', prefix: false})
        .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>')
        .addTo(map);

    return map;
}


/* ---- Shared helpers ---- */

/* Pan the background map so a single marker sits in the middle of the hero
   strip rather than the centre of the full (mostly-hidden) viewport. */
function panMarkerToHero(map, lat, lng, animate) {
    var hero = document.getElementById('hero');
    if (!hero) return;
    var rect = hero.getBoundingClientRect();
    var targetY = Math.round((rect.top + rect.bottom) / 2);
    var markerPt = map.latLngToContainerPoint(L.latLng(lat, lng));
    var dy = markerPt.y - targetY;
    if (Math.abs(dy) > 2) {
        map.panBy([0, dy], {animate: !!animate, duration: 0.3});
    }
}


/* ---- Location map: markers for child locations/POIs, expandable ---- */

function _makePinIcon(label, cls) {
    return L.divIcon({
        className: '',
        html: '<div class="w66-pin' + (cls ? ' ' + cls : '') + '">' + (label || '') + '</div>',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
    });
}

function _addSplitTiles(map) {
    // Labels-free base only — our own text markers replace OSM labels
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd', maxZoom: 19,
    }).addTo(map);
}

function initLocationMap(elementId, markers, options) {
    options = options || {};
    const map = L.map(elementId, {
        zoomControl: true,
        attributionControl: false,
        scrollWheelZoom: true,
    });

    _addSplitTiles(map);

    const group = L.featureGroup();
    group.addTo(map);
    map._markerGroup = group;

    // All markers available — starts as full pool; caller may expand via _setMarkers
    var _allMarkers = markers.slice();


    function _addDotMarker(m) {
        var highlight = !!m.highlight;
        var dotCls = highlight ? ' map-dot--highlight' : ' map-dot--grey';
        var dotHtml = '<i class="map-dot' + dotCls + '"></i>';
        var mk = L.marker([m.lat, m.lng], {
            icon: L.divIcon({
                className: 'map-label',
                html: '<div class="map-dot-hit">' + dotHtml + '</div>',
                iconSize: [0, 0], iconAnchor: [0, 0],
            }),
            zIndexOffset: -500,
        });
        if (m.name) {
            mk.bindTooltip(m.name, {
                className: 'map-name-tip',
                direction: 'top',
                offset: [0, -10],
                sticky: false,
            });
        }
        mk.addTo(group);
    }

    function _addLabelMarker(m, isSingle) {
        var highlight = !!m.highlight;
        var cls = isSingle && highlight ? ' map-label--highlight' : '';
        var inner = m.url
            ? '<a href="' + m.url + '">' + (m.name || '') + '</a>'
            : '<span>' + (m.name || '') + '</span>';
        L.marker([m.lat, m.lng], {
            icon: L.divIcon({
                className: 'map-label' + cls,
                html: '<i class="map-dot' + (highlight ? ' map-dot--highlight' : '') + '"></i>' + inner,
                iconSize: [0, 0], iconAnchor: [0, 0],
            }),
            zIndexOffset: 1000,
        }).addTo(group);
    }

    // Greedy deconfliction — walk pool top-down, place label only if it doesn't overlap.
    function _deconflict(pool, maxCount) {
        var PAD = 4;
        var PX_PER_CHAR = 7;
        var LINE_H = 18;
        var placed = [];
        var result = [];
        for (var i = 0; i < pool.length && result.length < maxCount; i++) {
            var m = pool[i];
            var pt = map.latLngToContainerPoint(L.latLng(m.lat, m.lng));
            var w = (m.name || '').length * PX_PER_CHAR + 8;
            var box = { x1: pt.x - w/2 - PAD, y1: pt.y - PAD,
                        x2: pt.x + w/2 + PAD, y2: pt.y + LINE_H + PAD };
            var overlaps = placed.some(function(p) {
                return box.x2 > p.x1 && box.x1 < p.x2 && box.y2 > p.y1 && box.y1 < p.y2;
            });
            if (!overlaps) { placed.push(box); result.push(m); }
        }
        return result;
    }

    function _renderMarkers(pool) {
        var bounds = map.getBounds();
        var inView = pool.filter(function(m) { return bounds.contains([m.lat, m.lng]); });
        inView.sort(function(a, b) {
            var hp = (b.highlight ? 1 : 0) - (a.highlight ? 1 : 0);
            return hp || (b.score || 0) - (a.score || 0);
        });
        group.clearLayers();
        var isSingle = pool.length === 1;
        // Only named markers are candidates for a label
        var named = inView.filter(function(m) { return !!m.name; });
        var labelled = _deconflict(named, 10);
        var labelledSet = {};
        labelled.forEach(function(m) { labelledSet[m.lat + ',' + m.lng] = true; });
        // Dots first (behind), then labels on top
        inView.forEach(function(m) {
            if (!labelledSet[m.lat + ',' + m.lng]) _addDotMarker(m);
        });
        labelled.forEach(function(m) { _addLabelMarker(m, isSingle); });
    }

    function _fitToGroup(grp, mkrs, opts) {
        if ((opts || {}).bounds) {
            map.fitBounds((opts).bounds, {animate: false});
        } else if (mkrs.length > 1) {
            map.fitBounds(grp.getBounds().pad(0.15));
        } else if (mkrs.length === 1) {
            var zoom = (opts || {}).isPoi ? 15 : 10;
            var center = L.latLng(mkrs[0].lat, mkrs[0].lng);
            map.setView(center, zoom, {animate: false});
            if ((opts || {}).isPoi) {
                panMarkerToHero(map, mkrs[0].lat, mkrs[0].lng, false);
            }
        }
    }

    // Initial render: fit map to top markers by score, then deconflict full pool.
    (function() {
        var sorted = markers.slice().sort(function(a, b) { return (b.score || 0) - (a.score || 0); });
        // Temporarily populate group with top markers so fitBounds works
        var forFit = sorted;
        forFit.forEach(function(m) { _addDotMarker(m); });
        _fitToGroup(group, forFit, options);
        // Re-render with deconfliction once the layout has settled
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                _renderMarkers(_allMarkers);
            });
        });
    })();

    // On zoom/pan, always re-run deconfliction so the best fitting labels are shown
    map.on('zoomend moveend', function() {
        _renderMarkers(_allMarkers);
    });

    // Called from template to expand/collapse marker pool.
    // Delays rendering until after layout settles so invalidateSize gets correct bounds.
    map._setMarkers = function(newMarkers) {
        _allMarkers = newMarkers.slice();
        requestAnimationFrame(function() {
            requestAnimationFrame(function() {
                map.invalidateSize();
                _renderMarkers(_allMarkers);
                if (group.getLayers().length > 1) {
                    map.fitBounds(group.getBounds().pad(0.15));
                }
            });
        });
    };

    L.control.attribution({position: 'bottomright', prefix: false})
        .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>')
        .addTo(map);

    // Fullscreen expand/collapse via button
    const wrapper = document.getElementById(elementId).closest('.map-wrapper');
    if (wrapper) {
        const el = document.getElementById(elementId);
        const btn = wrapper.querySelector('.map-expand-btn');
        if (btn) {
            function refitMap() {
                map.invalidateSize();
                if (markers.length > 1) {
                    map.fitBounds(group.getBounds().pad(0.15));
                } else if (markers.length === 1) {
                    map.setView([markers[0].lat, markers[0].lng], options.isPoi ? 15 : 10);
                }
            }

            function enterFullscreen() {
                wrapper.classList.add('map-fullscreen');
                btn.innerHTML = '&#x2715;';
                btn.title = 'Close';
                // Wait for the layout to settle before resizing the map
                requestAnimationFrame(function() {
                    requestAnimationFrame(refitMap);
                });
            }

            function exitFullscreen() {
                wrapper.classList.remove('map-fullscreen');
                btn.innerHTML = '&#x26F6;';
                btn.title = 'Fullscreen';
                requestAnimationFrame(function() {
                    requestAnimationFrame(refitMap);
                });
            }

            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (wrapper.classList.contains('map-fullscreen')) {
                    exitFullscreen();
                } else {
                    enterFullscreen();
                }
            });

            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape' && wrapper.classList.contains('map-fullscreen')) {
                    exitFullscreen();
                }
            });
        }
    }

    return map;
}

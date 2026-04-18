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
    }).setView([20, 0], 2);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
        maxZoom: 4,
        minZoom: 2,
    }).addTo(map);

    // Map GeoJSON continent names to our content slugs
    // GeoJSON has 7, we have 8 (Central America is part of North America in GeoJSON)
    const GEO_TO_SLUG = {
        "Africa": "africa",
        "Antarctica": "antarctica",
        "Asia": "asia",
        "Europe": "europe",
        "North America": "northamerica",
        "Oceania": "australiaandpacific",
        "South America": "southamerica",
    };

    // Build lookup from slug to content info
    const slugToInfo = {};
    w66continents.forEach(function(c) { slugToInfo[c.slug] = c; });

    // Label positions keyed by our slugs
    const LABEL_POS = {
        "africa": [15, 10],
        "antarctica": [-82, 0],
        "asia": [50, 90],
        "europe": [52, 8],
        "northamerica": [45, -115],
        "australiaandpacific": [-25, 112],
        "southamerica": [-8, -72],
        "centralamericathecaribbean": [18, -82],
    };

    fetch('/static/geo/continents.geo.json')
        .then(r => r.json())
        .then(data => {
            L.geoJSON(data, {
                style: function() {
                    return {
                        fillColor: W66_FILL,
                        fillOpacity: 0.6,
                        color: W66_RED,
                        weight: 1.5,
                    };
                },
                onEachFeature: function(feature, layer) {
                    const geoName = feature.properties.continent;
                    const slug = GEO_TO_SLUG[geoName];
                    const info = slug && slugToInfo[slug];
                    if (!info) return;

                    layer.on({
                        mouseover: function(e) {
                            e.target.setStyle({
                                fillColor: W66_FILL_HOVER,
                                fillOpacity: 0.8,
                                weight: 2,
                            });
                        },
                        mouseout: function(e) {
                            e.target.setStyle({
                                fillColor: W66_FILL,
                                fillOpacity: 0.6,
                                weight: 1.5,
                            });
                        },
                        click: function() {
                            window.location.href = info.url;
                        },
                    });
                },
            }).addTo(map);

            // Add labels from our content continents (all 8)
            w66continents.forEach(function(c) {
                const pos = LABEL_POS[c.slug];
                if (pos) {
                    L.marker(pos, {
                        icon: L.divIcon({
                            className: 'continent-label',
                            html: '<a href="' + c.url + '">' + c.title + '</a>',
                            iconSize: null,
                        }),
                    }).addTo(map);
                }
            });
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
        scrollWheelZoom: false,
    });

    _addSplitTiles(map);

    if (bounds) {
        map.fitBounds(bounds);
    }

    fetch('/static/geo/countries.geo.json')
        .then(r => r.json())
        .then(data => {
            // Filter to countries in this continent
            data.features = data.features.filter(f => {
                const slug = COUNTRY_SLUGS[f.properties.name];
                return slug && COUNTRY_CONTINENTS[slug] === continentSlug;
            });

            L.geoJSON(data, {
                style: function() {
                    return {
                        fillColor: W66_FILL,
                        fillOpacity: 0.5,
                        color: W66_RED,
                        weight: 1,
                    };
                },
                onEachFeature: function(feature, layer) {
                    const name = feature.properties.name;
                    const slug = COUNTRY_SLUGS[name];
                    if (!slug) return;

                    layer.bindTooltip(name, {
                        sticky: true,
                        className: 'country-tooltip',
                    });

                    layer.on({
                        mouseover: function(e) {
                            e.target.setStyle({
                                fillColor: W66_FILL_HOVER,
                                fillOpacity: 0.8,
                                weight: 2,
                            });
                        },
                        mouseout: function(e) {
                            e.target.setStyle({
                                fillColor: W66_FILL,
                                fillOpacity: 0.5,
                                weight: 1,
                            });
                        },
                        click: function() {
                            window.location.href = '/' + continentSlug + '/' + slug;
                        },
                    });
                },
            }).addTo(map);

            // Fit to the data if no explicit bounds
            if (!bounds && data.features.length > 0) {
                const geoLayer = L.geoJSON(data);
                map.fitBounds(geoLayer.getBounds().pad(0.1));
            }
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
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd', maxZoom: 19,
    }).addTo(map);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd', maxZoom: 19, pane: 'overlayPane',
    }).addTo(map);
}

function initLocationMap(elementId, markers, options) {
    options = options || {};
    const map = L.map(elementId, {
        zoomControl: false,
        attributionControl: false,
        scrollWheelZoom: false,
    });

    _addSplitTiles(map);

    const group = L.featureGroup();

    markers.forEach(function(m, i) {
        const isHighlight = !!m.highlight;
        const label = markers.length > 1 && !isHighlight
            ? String(i + 1).padStart(2, '0') : '';
        const cls = isHighlight ? 'accent' : '';
        const marker = L.marker([m.lat, m.lng], {
            icon: _makePinIcon(label, cls),
        }).addTo(group);

        if (m.name) {
            marker.bindTooltip(m.name, {direction: 'top', offset: [0, -14]});
        }
        if (m.url) {
            marker.on('click', function(e) {
                L.DomEvent.stopPropagation(e);
                window.location.href = m.url;
            });
        }
    });

    group.addTo(map);

    if (markers.length > 1) {
        map.fitBounds(group.getBounds().pad(0.15));
    } else if (markers.length === 1) {
        var zoom = options.isPoi ? 15 : 10;
        var center = L.latLng(markers[0].lat, markers[0].lng);
        map.setView(center, zoom, {animate: false});
        if (options.isPoi) {
            panMarkerToHero(map, markers[0].lat, markers[0].lng, false);
        }
    }

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

/* World66 Map — Leaflet-based maps for the travel guide */

const W66_RED = '#CC0000';
const W66_RED_HOVER = '#FF2222';
const W66_FILL = '#E8D0D0';
const W66_FILL_HOVER = '#F5E0E0';

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

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 8,
    }).addTo(map);

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
   strip rather than the centre of the full (mostly-hidden) viewport.
   Called on initial load and again whenever the hero height changes. */
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

function initLocationMap(elementId, markers, options) {
    options = options || {};
    const map = L.map(elementId, {
        zoomControl: false,
        attributionControl: false,
        scrollWheelZoom: false,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 18,
    }).addTo(map);

    const group = L.featureGroup();

    markers.forEach(function(m) {
        const isHighlight = !!m.highlight;
        const marker = L.circleMarker([m.lat, m.lng], {
            radius: isHighlight ? 8 : 5,
            fillColor: isHighlight ? W66_RED : '#999',
            fillOpacity: isHighlight ? 1 : 0.65,
            color: '#fff',
            weight: isHighlight ? 2 : 1,
        }).addTo(group);

        if (m.name) {
            marker.bindTooltip(m.name, {sticky: true});
        }
        if (m.url) {
            marker.on('click', function(e) {
                L.DomEvent.stopPropagation(e);
                window.location.href = m.url;
            });
            marker.setStyle({cursor: 'pointer'});
        }
    });

    group.addTo(map);

    if (markers.length > 1) {
        map.fitBounds(group.getBounds().pad(0.15));
    } else if (markers.length === 1) {
        var zoom = options.isPoi ? 15 : 10;
        var center = L.latLng(markers[0].lat, markers[0].lng);
        if (options.isPoi) {
            // Offset the initial center so the marker lands in the hero strip,
            // not behind the page content. Both setView calls are animate:false
            // so only the final position is ever painted.
            map.setView(center, zoom, {animate: false});
            var hero = document.getElementById('hero');
            if (hero) {
                var rect = hero.getBoundingClientRect();
                var heroMidY = (rect.top + rect.bottom) / 2;
                var dy = map.latLngToContainerPoint(center).y - heroMidY;
                if (Math.abs(dy) > 2) {
                    var currentCenter = map.getCenter();
                    var cPx = map.latLngToContainerPoint(currentCenter);
                    center = map.containerPointToLatLng(L.point(cPx.x, cPx.y + dy));
                }
            }
        }
        map.setView(center, zoom, {animate: false});
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

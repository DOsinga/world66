/* World66 Map — Leaflet-based maps for the travel guide */

const W66_RED = '#CC0000';
const W66_RED_HOVER = '#FF2222';
const W66_FILL = '#E8D0D0';
const W66_FILL_HOVER = '#F5E0E0';

/* ---- Home page: clickable continent map ---- */

function initContinentMap(elementId) {
    const map = L.map(elementId, {
        zoomControl: false,
        attributionControl: false,
        scrollWheelZoom: false,
        dragging: false,
        doubleClickZoom: false,
    }).setView([20, 0], 2);

    // Minimal light tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
        maxZoom: 4,
        minZoom: 2,
    }).addTo(map);

    // Label positions for each continent
    const CONTINENT_LABELS = {
        "Africa": [5, 20],
        "Antarctica": [-82, 0],
        "Asia": [40, 90],
        "Europe": [50, 15],
        "North America": [45, -100],
        "Oceania": [-25, 140],
        "South America": [-15, -58],
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
                    const name = feature.properties.continent;
                    const slug = CONTINENT_SLUGS[name];
                    if (!slug) return;

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
                            window.location.href = '/' + slug;
                        },
                    });

                    // Add continent label
                    const pos = CONTINENT_LABELS[name];
                    if (pos) {
                        L.marker(pos, {
                            icon: L.divIcon({
                                className: 'continent-label',
                                html: '<a href="/' + slug + '">' + name + '</a>',
                                iconSize: null,
                            }),
                        }).addTo(map);
                    }
                },
            }).addTo(map);
        });

    // Attribution in corner
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


/* ---- Location map: small map with a marker, expandable ---- */

function initLocationMap(elementId, lat, lng, name) {
    const map = L.map(elementId, {
        zoomControl: false,
        attributionControl: false,
        scrollWheelZoom: false,
    }).setView([lat, lng], 10);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 16,
    }).addTo(map);

    const marker = L.circleMarker([lat, lng], {
        radius: 6,
        fillColor: W66_RED,
        fillOpacity: 1,
        color: '#fff',
        weight: 2,
    }).addTo(map);

    if (name) {
        marker.bindTooltip(name, {permanent: false});
    }

    L.control.attribution({position: 'bottomright', prefix: false})
        .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>')
        .addTo(map);

    // Expand/collapse
    const el = document.getElementById(elementId);
    el.addEventListener('click', function() {
        el.classList.toggle('map-expanded');
        setTimeout(() => map.invalidateSize(), 300);
    });

    return map;
}

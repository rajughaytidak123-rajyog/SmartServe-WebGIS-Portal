/**
 * SmartServe GIS - Leaflet Map Manager Module
 * Manages tiles, boundary layers, POI marker clusters, proximity circles, and interactive popups.
 */

class MapManager {
    constructor(containerId = 'map') {
        this.containerId = containerId;
        this.map = null;
        this.baseLayers = {};
        this.boundaryLayer = null;
        this.poiClusterGroup = null;
        this.centerMarker = null;
        this.radiusCircle = null;
        this.markersMap = new Map(); // id -> L.marker
        this.onMapClickCallback = null;
    }

    /**
     * Initialize Leaflet Map with Base Layers and Controls
     */
    init() {
        // 1. Initialize Leaflet Map instance
        this.map = L.map(this.containerId, {
            center: CONFIG.MAP_CENTER,
            zoom: CONFIG.DEFAULT_ZOOM,
            minZoom: CONFIG.MIN_ZOOM,
            maxZoom: CONFIG.MAX_ZOOM,
            zoomControl: false // Custom position
        });

        // 2. Custom Zoom Control at Top-Right
        L.control.zoom({ position: 'topright' }).addTo(this.map);

        // 3. Metric Scale Control at Bottom-Right
        L.control.scale({
            position: 'bottomright',
            metric: true,
            imperial: false
        }).addTo(this.map);

        // 4. Base Tile Providers (Watermark-free, 100% free high-res map tiles)
        const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        });

        const esriStreet = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
            attribution: '&copy; Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, METI, TomTom',
            maxZoom: 19
        });

        const esriDark = L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
            attribution: '&copy; Esri, HERE, DeLorme, MapmyIndia, OpenStreetMap contributors',
            maxZoom: 16
        });

        const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: '&copy; Esri, Maxar, Earthstar Geographics, CNES/Airbus DS, USDA FSA, USGS, Aerogrid, IGN, IGP, and the GIS User Community',
            maxZoom: 18
        });

        // Default to OpenStreetMap for rich street details and zero watermarks
        osm.addTo(this.map);

        this.baseLayers = {
            "🗺️ OpenStreetMap": osm,
            "🏙️ Esri Streets": esriStreet,
            "🌙 Dark Mode": esriDark,
            "🛰️ Satellite": satellite
        };

        // 5. Initialize Marker Cluster Group
        this.poiClusterGroup = L.markerClusterGroup({
            chunkedLoading: true,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
            maxClusterRadius: 40,
            disableClusteringAtZoom: 15,
            iconCreateFunction: (cluster) => {
                const count = cluster.getChildCount();
                let sizeClass = 'cluster-small';
                if (count > 50) sizeClass = 'cluster-large';
                else if (count > 15) sizeClass = 'cluster-medium';

                return L.divIcon({
                    html: `<div class="custom-cluster ${sizeClass}"><span>${count}</span></div>`,
                    className: 'marker-cluster-custom',
                    iconSize: L.point(40, 40)
                });
            }
        });
        this.map.addLayer(this.poiClusterGroup);

        // 6. Listen to Map Click Events
        this.map.on('click', (e) => {
            if (this.onMapClickCallback) {
                this.onMapClickCallback(e.latlng.lat, e.latlng.lng);
            }
        });

        return this;
    }

    /**
     * Switch Base Tile Layer
     */
    setBaseLayer(layerName) {
        Object.values(this.baseLayers).forEach(layer => this.map.removeLayer(layer));
        if (this.baseLayers[layerName]) {
            this.baseLayers[layerName].addTo(this.map);
        }
    }

    /**
     * Render PMC & PCMC Municipal Boundary Polygons from GeoJSON
     */
    renderBoundaries(geoJsonData) {
        if (this.boundaryLayer) {
            this.map.removeLayer(this.boundaryLayer);
        }

        this.boundaryLayer = L.geoJSON(geoJsonData, {
            style: (feature) => {
                const code = feature.properties?.name_code || 'PMC';
                return CONFIG.BOUNDARY_STYLES[code] || CONFIG.BOUNDARY_STYLES['PMC'];
            },
            onEachFeature: (feature, layer) => {
                const props = feature.properties || {};
                const name = props.name || 'Municipal Boundary';
                const code = props.name_code || '';
                const area = props.area_sqkm ? `${props.area_sqkm} km²` : 'N/A';

                // Popup on boundary polygon
                const popupContent = `
                    <div class="boundary-popup">
                        <div class="boundary-badge ${code.toLowerCase()}">${code}</div>
                        <h4>${name}</h4>
                        <p><strong>Admin Level:</strong> Municipal Corporation</p>
                        <p><strong>Total Area:</strong> ${area}</p>
                    </div>
                `;
                layer.bindPopup(popupContent, { className: 'custom-boundary-popup' });

                // Hover highlight interactions
                layer.on({
                    mouseover: (e) => {
                        const l = e.target;
                        l.setStyle({ weight: 4, fillOpacity: 0.22 });
                    },
                    mouseout: (e) => {
                        this.boundaryLayer.resetStyle(e.target);
                    }
                });
            }
        }).addTo(this.map);

        return this;
    }

    /**
     * Toggle boundary overlay visibility
     */
    toggleBoundaries(visible) {
        if (!this.boundaryLayer) return;
        if (visible && !this.map.hasLayer(this.boundaryLayer)) {
            this.map.addLayer(this.boundaryLayer);
        } else if (!visible && this.map.hasLayer(this.boundaryLayer)) {
            this.map.removeLayer(this.boundaryLayer);
        }
    }

    /**
     * Set or Update Query Center Marker and Visual Radius Circle
     */
    setQueryCenter(lat, lon, radiusMeters = 2000, label = 'Search Center') {
        const latlng = L.latLng(lat, lon);

        // Center Pin Marker
        if (!this.centerMarker) {
            const centerIcon = L.divIcon({
                html: `<div class="query-center-pulse"><i class="fa-solid fa-crosshairs"></i></div>`,
                className: 'query-center-marker-icon',
                iconSize: [32, 32],
                iconAnchor: [16, 16]
            });

            this.centerMarker = L.marker(latlng, {
                icon: centerIcon,
                zIndexOffset: 1000,
                draggable: true
            }).addTo(this.map);

            this.centerMarker.on('dragend', (e) => {
                const pos = e.target.getLatLng();
                if (this.onMapClickCallback) {
                    this.onMapClickCallback(pos.lat, pos.lng);
                }
            });
        } else {
            this.centerMarker.setLatLng(latlng);
        }

        this.centerMarker.bindTooltip(`📍 ${label}`, {
            permanent: false,
            direction: 'top',
            className: 'query-center-tooltip'
        });

        // Radius Circle (Fresh Electric Cyan Glow)
        if (!this.radiusCircle) {
            this.radiusCircle = L.circle(latlng, {
                radius: radiusMeters,
                color: '#00f2fe',
                fillColor: '#38bdf8',
                fillOpacity: 0.18,
                weight: 2.5,
                dashArray: '6, 6'
            }).addTo(this.map);
        } else {
            this.radiusCircle.setLatLng(latlng);
            this.radiusCircle.setRadius(radiusMeters);
        }
    }

    /**
     * Update only the radius circle size dynamically
     */
    updateRadiusCircle(radiusMeters) {
        if (this.radiusCircle) {
            this.radiusCircle.setRadius(radiusMeters);
        }
    }

    /**
     * Fit map view smoothly to the current radius circle bounds
     */
    fitToRadiusCircle() {
        if (this.radiusCircle) {
            this.map.fitBounds(this.radiusCircle.getBounds(), { padding: [40, 40], maxZoom: 16 });
        }
    }

    /**
     * Remove Search Center Marker and Radius Circle
     */
    clearQueryCenter() {
        if (this.centerMarker) {
            this.map.removeLayer(this.centerMarker);
            this.centerMarker = null;
        }
        if (this.radiusCircle) {
            this.map.removeLayer(this.radiusCircle);
            this.radiusCircle = null;
        }
    }

    /**
     * Create Custom FontAwesome DivIcon for POI
     */
    createPOIIcon(subcatKey) {
        const meta = CONFIG.getSubcategoryMeta(subcatKey);
        return L.divIcon({
            html: `
                <div class="custom-poi-marker" style="--marker-color: ${meta.color};">
                    <div class="marker-pin"><i class="fa-solid ${meta.icon}"></i></div>
                </div>
            `,
            className: 'poi-div-icon',
            iconSize: [32, 40],
            iconAnchor: [16, 38],
            popupAnchor: [0, -36]
        });
    }

    /**
     * Render List of POIs on Map
     */
    renderPOIs(pois = [], fitBounds = false) {
        this.poiClusterGroup.clearLayers();
        this.markersMap.clear();

        if (!pois || pois.length === 0) return;

        const bounds = L.latLngBounds();

        pois.forEach(poi => {
            if (!poi.latitude || !poi.longitude) return;

            const icon = this.createPOIIcon(poi.subcategory);
            const marker = L.marker([poi.latitude, poi.longitude], { icon });

            // Build rich popup content
            const popupHtml = this.buildPopupContent(poi);
            marker.bindPopup(popupHtml, {
                className: 'custom-poi-popup',
                maxWidth: 320
            });

            this.poiClusterGroup.addLayer(marker);
            this.markersMap.set(poi.id, marker);
            bounds.extend([poi.latitude, poi.longitude]);
        });

        if (fitBounds && pois.length > 0 && bounds.isValid()) {
            this.map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
        }
    }

    /**
     * Build rich HTML Popup Card for a POI
     */
    buildPopupContent(poi) {
        const meta = CONFIG.getSubcategoryMeta(poi.subcategory);
        const name = poi.name || 'Unnamed Facility';
        const muni = poi.municipality || 'PMC';
        const muniBadgeClass = muni === 'PMC' ? 'muni-pmc' : 'muni-pcmc';

        // Distance & ETA if available
        let distanceSection = '';
        if (poi.distance_meters !== undefined && poi.distance_meters !== null) {
            const dist = poi.distance_meters < 1000 
                ? `${Math.round(poi.distance_meters)} m` 
                : `${(poi.distance_meters / 1000).toFixed(2)} km`;

            // Walking speed ~ 80 m/min, Driving speed ~ 400 m/min (24 km/h)
            const walkMins = Math.max(1, Math.round(poi.distance_meters / 80));
            const driveMins = Math.max(1, Math.round(poi.distance_meters / 400));

            distanceSection = `
                <div class="popup-distance-box">
                    <div class="dist-val"><i class="fa-solid fa-route"></i> <strong>${dist}</strong> away</div>
                    <div class="eta-tags">
                        <span title="Estimated walking time"><i class="fa-solid fa-person-walking"></i> ~${walkMins} min</span>
                        <span title="Estimated driving time"><i class="fa-solid fa-car"></i> ~${driveMins} min</span>
                    </div>
                </div>
            `;
        }

        // Contact / Info Details
        let contactRows = '';
        if (poi.phone) {
            contactRows += `<div class="popup-row"><i class="fa-solid fa-phone"></i> <a href="tel:${poi.phone}">${poi.phone}</a></div>`;
        }
        if (poi.website) {
            contactRows += `<div class="popup-row"><i class="fa-solid fa-globe"></i> <a href="${poi.website}" target="_blank" rel="noopener">Visit Website</a></div>`;
        }
        if (poi.address) {
            contactRows += `<div class="popup-row"><i class="fa-solid fa-location-dot"></i> <span>${poi.address}</span></div>`;
        }

        // Navigation Directions Link
        const gmapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${poi.latitude},${poi.longitude}`;

        return `
            <div class="poi-popup-card">
                <div class="popup-header" style="border-left-color: ${meta.color};">
                    <div class="popup-category">
                        <span class="cat-badge" style="background: ${meta.color}22; color: ${meta.color}; border: 1px solid ${meta.color}55;">
                            <i class="fa-solid ${meta.icon}"></i> ${meta.name}
                        </span>
                        <span class="muni-badge ${muniBadgeClass}">${muni}</span>
                    </div>
                    <h3 class="popup-title">${name}</h3>
                </div>

                ${distanceSection}

                <div class="popup-body">
                    ${contactRows || '<div class="popup-row text-muted"><em>Standard public facility record</em></div>'}
                </div>

                <div class="popup-footer">
                    <a href="${gmapsUrl}" target="_blank" rel="noopener" class="btn-directions">
                        <i class="fa-solid fa-diamond-turn-right"></i> Get Directions
                    </a>
                </div>
            </div>
        `;
    }

    /**
     * Pan and zoom to specific POI and open popup (creates marker if not yet in cluster)
     */
    focusPOI(poiId, lat, lon, poiData = null) {
        if (!lat || !lon) return;

        this.map.setView([lat, lon], 16, { animate: true });

        const marker = this.markersMap.get(poiId);
        if (marker) {
            // Uncluster if needed and open popup
            this.poiClusterGroup.zoomToShowLayer(marker, () => {
                marker.openPopup();
            });
        } else if (poiData) {
            // If marker was not in current filter group, create it dynamically in cluster
            const icon = this.createPOIIcon(poiData.subcategory);
            const dynamicMarker = L.marker([lat, lon], { icon });
            const popupHtml = this.buildPopupContent(poiData);
            dynamicMarker.bindPopup(popupHtml, {
                className: 'custom-poi-popup',
                maxWidth: 320
            });
            this.poiClusterGroup.addLayer(dynamicMarker);
            this.markersMap.set(poiId, dynamicMarker);

            setTimeout(() => {
                this.poiClusterGroup.zoomToShowLayer(dynamicMarker, () => {
                    dynamicMarker.openPopup();
                });
            }, 100);
        }
    }

    /**
     * Set click listener callback
     */
    onMapClick(callback) {
        this.onMapClickCallback = callback;
    }

    /**
     * Reset View to Pune City Center
     */
    resetView() {
        this.map.setView(CONFIG.MAP_CENTER, CONFIG.DEFAULT_ZOOM, { animate: true });
    }
}

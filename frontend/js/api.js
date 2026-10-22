/**
 * SmartServe GIS - API Service Module
 * Handles all REST communication with the FastAPI Spatial Backend.
 */

const API = {
    /**
     * Generic fetch wrapper with error handling and JSON parsing.
     */
    async _fetch(endpoint, params = {}) {
        try {
            const url = new URL(`${CONFIG.API_BASE_URL}${endpoint}`);
            Object.entries(params).forEach(([key, val]) => {
                if (val !== undefined && val !== null && val !== '') {
                    url.searchParams.append(key, val);
                }
            });

            const response = await fetch(url.toString(), {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP Error ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`[API Error] Failed fetching ${endpoint}:`, error);
            throw error;
        }
    },

    // ==========================================
    // 1. BOUNDARIES
    // ==========================================
    async getBoundaries() {
        return await this._fetch('/boundaries/');
    },

    // ==========================================
    // 2. CATEGORIES
    // ==========================================
    async getCategoryTree() {
        return await this._fetch('/categories/tree');
    },

    async getCategories() {
        return await this._fetch('/categories/');
    },

    // ==========================================
    // 3. SERVICES / SPATIAL QUERIES
    // ==========================================
    /**
     * Radius Proximity Search (ST_DWithin)
     */
    async getNearbyServices({ lat, lon, radius_meters = 2000, q = null, category = null, subcategory = null, municipality = null, limit = 200 }) {
        return await this._fetch('/services/nearby', {
            lat,
            lon,
            radius_meters,
            q,
            category,
            subcategory,
            municipality,
            limit
        });
    },

    /**
     * K-Nearest Neighbors (PostGIS <-> Operator)
     */
    async getKnnServices({ lat, lon, k = 5, q = null, category = null, subcategory = null, municipality = null }) {
        return await this._fetch('/services/knn', {
            lat,
            lon,
            k,
            q,
            category,
            subcategory,
            municipality
        });
    },

    /**
     * Multi-Criteria Keyword & Attribute Search
     */
    async searchServices({ q = '', category = null, subcategory = null, municipality = null, limit = 50, offset = 0 }) {
        return await this._fetch('/services/search', {
            q,
            category,
            subcategory,
            municipality,
            limit,
            offset
        });
    },

    /**
     * Real-time Autocomplete Suggestions
     */
    async getAutocomplete(q, limit = 8) {
        if (!q || !q.trim()) return [];
        return await this._fetch('/services/autocomplete', {
            q: q.trim(),
            limit
        });
    },

    /**
     * Native GeoJSON POI Stream
     */
    async getGeoJson({ category = null, subcategory = null, municipality = null, bbox = null, limit = 500 }) {
        const params = { category, subcategory, municipality, limit };
        if (bbox && bbox.length === 4) {
            params.min_lon = bbox[0];
            params.min_lat = bbox[1];
            params.max_lon = bbox[2];
            params.max_lat = bbox[3];
        }
        return await this._fetch('/services/geojson', params);
    },

    /**
     * Single POI Details
     */
    async getServiceById(id) {
        return await this._fetch(`/services/${id}`);
    },

    // ==========================================
    // 4. SPATIAL ANALYTICS
    // ==========================================
    async getAnalyticsOverview() {
        return await this._fetch('/analytics/overview');
    },

    async getDensityMetrics() {
        return await this._fetch('/analytics/density');
    },

    async getNearbySummary({ lat, lon, radius_meters = 2000 }) {
        return await this._fetch('/analytics/nearby-summary', {
            lat,
            lon,
            radius_meters
        });
    },

    // ==========================================
    // 5. SYSTEM HEALTH CHECK
    // ==========================================
    async checkHealth() {
        try {
            const res = await fetch('http://127.0.0.1:8000/health');
            return await res.json();
        } catch (e) {
            return { status: 'offline', error: e.message };
        }
    }
};

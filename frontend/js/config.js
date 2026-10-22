/**
 * SmartServe GIS - Application Configuration
 * Contains API endpoints, spatial constants, fresh vibrant color schemes,
 * and category icon mappings precisely aligned with the SmartServe database.
 */

const CONFIG = {
    // Backend API Base URL (FastAPI Server)
    API_BASE_URL: 'http://127.0.0.1:8000/api/v1',

    // Default Spatial Extent (Pune City Center)
    MAP_CENTER: [18.5204, 73.8567],
    DEFAULT_ZOOM: 12,
    MIN_ZOOM: 10,
    MAX_ZOOM: 18,

    // Study Area Bounds (Pune & Pimpri-Chinchwad bounding box)
    STUDY_BOUNDS: [
        [18.35, 73.70], // Southwest
        [18.75, 74.05]  // Northeast
    ],

    // Default Proximity Settings
    DEFAULT_RADIUS_METERS: 2000,
    MIN_RADIUS_METERS: 500,
    MAX_RADIUS_METERS: 10000,
    RADIUS_STEP: 250,

    // Fresh & Vibrant Category Metadata (Colors & FontAwesome 6 icons)
    CATEGORIES: {
        'Healthcare': {
            icon: 'fa-kit-medical',
            color: '#ff4757', // Coral Rose
            badgeClass: 'badge-health',
            subcategories: {
                'Hospital': { name: 'Hospitals', icon: 'fa-hospital', color: '#ff4757' },
                'Clinic': { name: 'Clinics & Dispensaries', icon: 'fa-user-doctor', color: '#ff6b81' },
                'Pharmacy': { name: 'Pharmacies & Chemists', icon: 'fa-pills', color: '#ff7979' }
            }
        },
        'Emergency': {
            icon: 'fa-triangle-exclamation',
            color: '#ff3838', // Bright Neon Red
            badgeClass: 'badge-emergency',
            subcategories: {
                'Fire Station': { name: 'Fire Stations', icon: 'fa-fire-extinguisher', color: '#ff3838' },
                'Police Station': { name: 'Police Stations', icon: 'fa-shield-halved', color: '#3742fa' }
            }
        },
        'Education': {
            icon: 'fa-graduation-cap',
            color: '#5352ed', // Electric Indigo
            badgeClass: 'badge-edu',
            subcategories: {
                'School': { name: 'Schools', icon: 'fa-school', color: '#3867d6' },
                'College': { name: 'Colleges & Institutes', icon: 'fa-graduation-cap', color: '#5352ed' }
            }
        },
        'Transport': {
            icon: 'fa-bus-simple',
            color: '#ff9f43', // Warm Tangerine
            badgeClass: 'badge-trans',
            subcategories: {
                'Bus Station': { name: 'Bus Stations / Stops', icon: 'fa-bus', color: '#ff9f43' },
                'Metro Station': { name: 'Metro Stations', icon: 'fa-train-subway', color: '#fed330' },
                'Petrol Pump': { name: 'Petrol / Fuel Pumps', icon: 'fa-gas-pump', color: '#fa8231' },
                'EV Charging': { name: 'EV Charging Stations', icon: 'fa-charging-station', color: '#26de81' }
            }
        },
        'Finance': {
            icon: 'fa-building-columns',
            color: '#10b981', // Mint Emerald
            badgeClass: 'badge-fin',
            subcategories: {
                'Bank': { name: 'Banks', icon: 'fa-landmark', color: '#10b981' },
                'ATM': { name: 'ATMs', icon: 'fa-money-bill-wave', color: '#2ed573' }
            }
        },
        'Food': {
            icon: 'fa-utensils',
            color: '#feca57', // Honey Gold
            badgeClass: 'badge-food',
            subcategories: {
                'Restaurant': { name: 'Restaurants', icon: 'fa-utensils', color: '#feca57' },
                'Cafe': { name: 'Cafes', icon: 'fa-mug-saucer', color: '#ff9f1a' },
                'Bakery': { name: 'Bakeries', icon: 'fa-cake-candles', color: '#e58e26' }
            }
        },
        'Shopping': {
            icon: 'fa-cart-shopping',
            color: '#a55eea', // Vivid Violet
            badgeClass: 'badge-shop',
            subcategories: {
                'Supermarket': { name: 'Supermarkets', icon: 'fa-cart-shopping', color: '#a55eea' },
                'Shopping Mall': { name: 'Shopping Malls', icon: 'fa-shop', color: '#8854d0' }
            }
        },
        'Recreation': {
            icon: 'fa-tree',
            color: '#1dd1a1', // Fresh Spring Jade
            badgeClass: 'badge-rec',
            subcategories: {
                'Park': { name: 'Parks & Gardens', icon: 'fa-tree', color: '#1dd1a1' }
            }
        },
        'Accommodation': {
            icon: 'fa-hotel',
            color: '#0abde3', // Ocean Azure
            badgeClass: 'badge-accom',
            subcategories: {
                'Hotel': { name: 'Hotels & Lodging', icon: 'fa-hotel', color: '#0abde3' }
            }
        }
    },

    // Flexible Subcategory lookup helper
    getSubcategoryMeta(subcatName) {
        if (!subcatName) return { name: 'Facility', icon: 'fa-location-dot', color: '#4facfe' };
        
        const cleanName = subcatName.trim();
        const lowerName = cleanName.toLowerCase().replace(/_/g, ' ');

        for (const [catName, catData] of Object.entries(this.CATEGORIES)) {
            for (const [sKey, sData] of Object.entries(catData.subcategories)) {
                if (sKey.toLowerCase() === lowerName || sKey.toLowerCase() === cleanName.toLowerCase()) {
                    return {
                        category: catName,
                        name: sKey,
                        displayName: sData.name,
                        icon: sData.icon,
                        color: sData.color
                    };
                }
            }
        }

        // Fallback
        return {
            category: 'Other',
            name: cleanName,
            displayName: cleanName,
            icon: 'fa-map-pin',
            color: '#38bdf8'
        };
    },

    // Fresh Municipal boundary styling (PMC Cyan / PCMC Mint)
    BOUNDARY_STYLES: {
        'PMC': {
            color: '#0984e3',
            fillColor: '#74b9ff',
            fillOpacity: 0.15,
            weight: 3,
            dashArray: '5, 5'
        },
        'PCMC': {
            color: '#00b894',
            fillColor: '#55efc4',
            fillOpacity: 0.15,
            weight: 3,
            dashArray: '5, 5'
        }
    }
};

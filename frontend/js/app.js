/**
 * SmartServe GIS - Main Application Controller
 * Wires UI controls, category filters, proximity search, KNN finder, and results panels.
 */

class SmartServeApp {
    constructor() {
        this.mapManager = null;
        this.analyticsManager = null;
        
        // App State
        this.state = {
            activeTab: 'explore', // 'explore' | 'radius' | 'knn'
            currentLocation: { lat: 18.5204, lon: 73.8567, label: 'Pune Center' },
            radiusMeters: 2000,
            knnK: 5,
            selectedMunicipality: '', // '' = all, 'PMC', 'PCMC'
            selectedCategory: '',
            selectedSubcategory: '',
            searchQuery: '',
            categoriesTree: [],
            pois: [],
            isLoading: false
        };

        this.searchDebounceTimer = null;
        this.autocompleteDebounceTimer = null;
        this.currentSuggestions = [];
        this.selectedSuggestionIndex = -1;
    }

    /**
     * Bootstraps the application
     */
    async init() {
        console.log('[SmartServe GIS] Initializing Application...');

        // 1. Initialize Map and Analytics
        this.mapManager = new MapManager('map').init();
        this.analyticsManager = new AnalyticsManager();

        // 2. Setup Map Click Handler for Spatial Queries
        this.mapManager.onMapClick((lat, lon) => {
            this.handleMapClickLocation(lat, lon);
        });

        // 3. Register UI Event Listeners & Autocomplete
        this.registerEventListeners();
        this.setupSearchAutocomplete();

        // 4. Check Health & Load Core Data
        await this.loadInitialData();

        console.log('[SmartServe GIS] Initialization Complete.');
    }

    /**
     * Load initial dataset (Boundaries, Categories, and Default Services)
     */
    async loadInitialData() {
        this.showLoading(true);

        try {
            // Check Backend API Connection
            const health = await API.checkHealth();
            this.updateHealthBadge(health);

            // Fetch Boundaries & Categories in Parallel
            const [boundaries, categoryTree] = await Promise.all([
                API.getBoundaries().catch(err => {
                    console.warn('[Warning] Boundaries failed to load:', err);
                    return null;
                }),
                API.getCategoryTree().catch(err => {
                    console.warn('[Warning] Categories failed to load:', err);
                    return [];
                })
            ]);

            // Render Administrative Boundaries
            if (boundaries) {
                this.mapManager.renderBoundaries(boundaries);
            }

            // Populate Category Navigation
            if (categoryTree && categoryTree.length > 0) {
                this.state.categoriesTree = categoryTree;
                this.renderCategorySidebar(categoryTree);
                this.populateSubcategoryDropdowns(categoryTree);
            }

            // Set initial query center & radius circle buffer on map
            this.mapManager.setQueryCenter(
                this.state.currentLocation.lat,
                this.state.currentLocation.lon,
                this.state.radiusMeters,
                this.state.currentLocation.label
            );

            // Automatically attempt GPS Geolocation on startup (silent auto-mode)
            this.handleGeolocation(true);

            // Initial Load: Show services within the user's active radius
            await this.executeRadiusSearch();

            // Handle URL parameters for direct view showcase (e.g., ?tab=radius or ?modal=analytics)
            try {
                const urlParams = new URLSearchParams(window.location.search);
                const reqTab = urlParams.get('tab');
                if (reqTab && ['explore', 'radius', 'knn'].includes(reqTab)) {
                    this.switchTab(reqTab);
                }
                if (urlParams.get('modal') === 'analytics') {
                    setTimeout(() => {
                        const btn = document.getElementById('btn-open-analytics');
                        if (btn) btn.click();
                    }, 600);
                }
            } catch (paramErr) {
                console.warn('URL parameter parsing skipped:', paramErr);
            }

        } catch (error) {
            console.error('[App Error] Initial data load failed:', error);
            this.showToast('Could not connect to backend server. Make sure FastAPI is running on port 8000.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Register DOM Event Listeners
     */
    registerEventListeners() {
        // Mode Tabs Switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // Municipality Filter Pills
        document.querySelectorAll('.muni-pill').forEach(pill => {
            pill.addEventListener('click', (e) => {
                document.querySelectorAll('.muni-pill').forEach(p => p.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.state.selectedMunicipality = e.currentTarget.dataset.muni || '';
                this.triggerActiveTabSearch();
            });
        });

        // Base Tile Switcher
        const baseLayerSelect = document.getElementById('basemap-select');
        if (baseLayerSelect) {
            baseLayerSelect.addEventListener('change', (e) => {
                this.mapManager.setBaseLayer(e.target.value);
            });
        }

        // Boundary Overlay Toggle
        const boundaryCheckbox = document.getElementById('toggle-boundaries');
        if (boundaryCheckbox) {
            boundaryCheckbox.addEventListener('change', (e) => {
                this.mapManager.toggleBoundaries(e.target.checked);
            });
        }

        // Geolocation "Locate Me" Buttons
        document.querySelectorAll('.btn-locate-me').forEach(btn => {
            btn.addEventListener('click', () => this.handleGeolocation(false));
        });

        // Radius Quick Selector Pills (Explore tab)
        document.querySelectorAll('.radius-pill').forEach(pill => {
            pill.addEventListener('click', (e) => {
                const r = parseInt(e.currentTarget.dataset.radius, 10);
                if (r) this.setRadiusMeters(r);
            });
        });

        // Radius Slider
        const radiusSlider = document.getElementById('radius-slider');
        if (radiusSlider) {
            radiusSlider.addEventListener('input', (e) => {
                const val = parseInt(e.target.value, 10);
                this.setRadiusMeters(val);
            });
        }

        // Radius Subcategory Filter
        const radiusSubcatSelect = document.getElementById('radius-subcat-select');
        if (radiusSubcatSelect) {
            radiusSubcatSelect.addEventListener('change', (e) => {
                this.state.selectedSubcategory = e.target.value;
                this.executeRadiusSearch();
            });
        }

        // KNN Subcategory Selector
        const knnSubcatSelect = document.getElementById('knn-subcat-select');
        if (knnSubcatSelect) {
            knnSubcatSelect.addEventListener('change', (e) => {
                this.state.selectedSubcategory = e.target.value;
                this.executeKnnSearch();
            });
        }

        // KNN K Counter Buttons
        document.querySelectorAll('.k-pill').forEach(pill => {
            pill.addEventListener('click', (e) => {
                document.querySelectorAll('.k-pill').forEach(p => p.classList.remove('active'));
                e.currentTarget.classList.add('active');
                this.state.knnK = parseInt(e.currentTarget.dataset.k, 10) || 5;
                this.executeKnnSearch();
            });
        });

        // Clear / Reset Button
        const resetBtn = document.getElementById('btn-reset-filters');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetFilters());
        }

        // Analytics Modal Trigger
        const analyticsBtn = document.getElementById('btn-open-analytics');
        const analyticsModal = document.getElementById('analytics-modal');
        const closeAnalyticsBtn = document.getElementById('btn-close-analytics');

        if (analyticsBtn && analyticsModal) {
            analyticsBtn.addEventListener('click', () => {
                analyticsModal.classList.add('active');
                this.analyticsManager.loadAndRender();
            });
        }
        if (closeAnalyticsBtn && analyticsModal) {
            closeAnalyticsBtn.addEventListener('click', () => {
                analyticsModal.classList.remove('active');
            });
        }

        // Help Modal Trigger
        const helpBtn = document.getElementById('btn-open-help');
        const helpModal = document.getElementById('help-modal');
        const closeHelpBtn = document.getElementById('btn-close-help');

        if (helpBtn && helpModal) {
            helpBtn.addEventListener('click', () => helpModal.classList.add('active'));
        }
        if (closeHelpBtn && helpModal) {
            closeHelpBtn.addEventListener('click', () => helpModal.classList.remove('active'));
        }

        // Close Modals on Backdrop Click
        window.addEventListener('click', (e) => {
            if (e.target === analyticsModal) analyticsModal.classList.remove('active');
            if (e.target === helpModal) helpModal.classList.remove('active');
        });

        // Results Drawer Collapse / Expand Toggle
        const resultsDrawer = document.getElementById('results-drawer');
        const drawerHeader = document.getElementById('results-drawer-header');
        if (resultsDrawer && drawerHeader) {
            drawerHeader.addEventListener('click', () => {
                resultsDrawer.classList.toggle('collapsed');
            });
        }

        // Sidebar Toggle for Mobile
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');
        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
            });
        }
    }

    /**
     * Update Search Radius in meters and synchronize all UI inputs & circle
     */
    setRadiusMeters(meters) {
        this.state.radiusMeters = meters;

        // 1. Sync Slider
        const slider = document.getElementById('radius-slider');
        if (slider) slider.value = meters;

        // 2. Sync Labels
        const radiusText = meters >= 1000 ? `${(meters / 1000).toFixed(1)} km` : `${meters} m`;
        const radiusValDisplay = document.getElementById('radius-val-display');
        if (radiusValDisplay) radiusValDisplay.textContent = radiusText;

        const exploreRadiusText = document.getElementById('explore-radius-text');
        if (exploreRadiusText) exploreRadiusText.textContent = radiusText;

        const exploreRadiusBadge = document.getElementById('explore-radius-badge');
        if (exploreRadiusBadge) exploreRadiusBadge.textContent = `${radiusText} radius`;

        // 3. Sync Active Pills
        document.querySelectorAll('.radius-pill').forEach(pill => {
            const r = parseInt(pill.dataset.radius, 10);
            pill.classList.toggle('active', r === meters);
        });

        // 4. Update Map Circle and View Bounds
        this.mapManager.updateRadiusCircle(meters);
        this.mapManager.fitToRadiusCircle();

        // 5. Re-execute Search with new radius
        this.executeRadiusSearch();
    }

    /**
     * Switch Active Workflow Tab (Explore / Radius / KNN)
     */
    switchTab(tabName) {
        this.state.activeTab = tabName;

        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update panel contents
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `panel-${tabName}`);
        });

        if (tabName === 'explore') {
            this.mapManager.setQueryCenter(
                this.state.currentLocation.lat,
                this.state.currentLocation.lon,
                this.state.radiusMeters,
                this.state.currentLocation.label
            );
            this.executeRadiusSearch();
            this.mapManager.fitToRadiusCircle();
        } else if (tabName === 'radius') {
            const radiusSubcat = document.getElementById('radius-subcat-select')?.value || this.state.selectedSubcategory || '';
            this.state.selectedSubcategory = radiusSubcat;

            this.mapManager.setQueryCenter(
                this.state.currentLocation.lat,
                this.state.currentLocation.lon,
                this.state.radiusMeters,
                this.state.currentLocation.label
            );
            this.executeRadiusSearch();
            this.mapManager.fitToRadiusCircle();
        } else if (tabName === 'knn') {
            const knnSubcat = document.getElementById('knn-subcat-select')?.value || this.state.selectedSubcategory || 'Hospital';
            this.state.selectedSubcategory = knnSubcat;

            this.mapManager.setQueryCenter(
                this.state.currentLocation.lat,
                this.state.currentLocation.lon,
                0,
                this.state.currentLocation.label
            );
            this.executeKnnSearch();
        }
    }

    /**
     * Handle user click on Leaflet map to re-center proximity or KNN search
     */
    handleMapClickLocation(lat, lon) {
        this.state.currentLocation = {
            lat: Number(lat.toFixed(6)),
            lon: Number(lon.toFixed(6)),
            label: `Point (${lat.toFixed(4)}, ${lon.toFixed(4)})`
        };

        // Update UI location text
        document.querySelectorAll('.active-loc-display').forEach(el => {
            el.textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
        });

        if (this.state.activeTab === 'knn') {
            this.mapManager.setQueryCenter(lat, lon, 0, 'Custom Map Point');
            this.executeKnnSearch();
        } else {
            this.mapManager.setQueryCenter(lat, lon, this.state.radiusMeters, 'Custom Map Point');
            this.executeRadiusSearch();
            this.mapManager.fitToRadiusCircle();
        }

        const subcatDesc = this.state.selectedSubcategory ? ` for ${this.state.selectedSubcategory}` : '';
        this.showToast(`Search origin moved to (${lat.toFixed(4)}, ${lon.toFixed(4)})${subcatDesc}`, 'info');
    }

    /**
     * Trigger Browser Geolocation (GPS)
     */
    handleGeolocation(isAuto = false) {
        if (!navigator.geolocation) {
            if (!isAuto) this.showToast('Geolocation is not supported by your browser.', 'warning');
            return;
        }

        if (!isAuto) this.showToast('Detecting your GPS location...', 'info');

        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const lat = Number(pos.coords.latitude.toFixed(6));
                const lon = Number(pos.coords.longitude.toFixed(6));
                this.state.currentLocation = {
                    lat,
                    lon,
                    label: 'Your GPS Location'
                };

                document.querySelectorAll('.active-loc-display').forEach(el => {
                    el.textContent = `${lat.toFixed(4)}, ${lon.toFixed(4)}`;
                });

                this.mapManager.map.setView([lat, lon], 14, { animate: true });

                if (this.state.activeTab === 'knn') {
                    this.mapManager.setQueryCenter(lat, lon, 0, 'Your GPS Location');
                    this.executeKnnSearch();
                } else {
                    this.mapManager.setQueryCenter(lat, lon, this.state.radiusMeters, 'Your GPS Location');
                    this.executeRadiusSearch();
                    this.mapManager.fitToRadiusCircle();
                }

                this.showToast('📍 Location set to your GPS position!', 'success');
            },
            (err) => {
                console.warn('[Geolocation Info]', err.message);
                if (!isAuto) {
                    this.showToast('Location access denied. Click anywhere on map to set origin.', 'warning');
                }
            },
            { enableHighAccuracy: true, timeout: 7000 }
        );
    }

    /**
     * Trigger search for currently active tab
     */
    triggerActiveTabSearch() {
        if (this.state.activeTab === 'knn') this.executeKnnSearch();
        else this.executeRadiusSearch();
    }

    /**
     * 1. Mode: Explore & Multi-Attribute Search
     */
    async executeExploreSearch() {
        // In location-first mode, explore delegates to proximity radius search
        await this.executeRadiusSearch();
    }

    /**
     * 2. Mode: Proximity Radius Search (ST_DWithin on PostGIS Geography)
     */
    async executeRadiusSearch() {
        this.showLoading(true);
        try {
            const radiusSubcat = this.state.selectedSubcategory || document.getElementById('radius-subcat-select')?.value || null;

            const results = await API.getNearbyServices({
                lat: this.state.currentLocation.lat,
                lon: this.state.currentLocation.lon,
                radius_meters: this.state.radiusMeters,
                q: this.state.searchQuery || null,
                subcategory: radiusSubcat || null,
                municipality: this.state.selectedMunicipality || null,
                limit: 300
            });

            this.state.pois = results.items || [];
            this.renderResultsList(this.state.pois, 'radius');
            this.mapManager.renderPOIs(this.state.pois, false);

            const radiusText = this.state.radiusMeters >= 1000 
                ? `${(this.state.radiusMeters / 1000).toFixed(1)} km` 
                : `${this.state.radiusMeters} m`;

            const subcatMeta = radiusSubcat ? CONFIG.getSubcategoryMeta(radiusSubcat) : null;
            const targetLabel = subcatMeta ? `${subcatMeta.name}s` : 'Services';

            this.updateResultsHeaderCount(results.total, `${targetLabel} Within ${radiusText}`);
        } catch (error) {
            console.error('[Radius Search Error]', error);
            this.showToast('Radius search failed. Check backend connection.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * 3. Mode: K-Nearest Neighbors (PostGIS <-> operator)
     */
    async executeKnnSearch() {
        this.showLoading(true);
        try {
            const knnSubcat = document.getElementById('knn-subcat-select')?.value || this.state.selectedSubcategory || null;

            const results = await API.getKnnServices({
                lat: this.state.currentLocation.lat,
                lon: this.state.currentLocation.lon,
                k: this.state.knnK,
                q: this.state.searchQuery || null,
                subcategory: knnSubcat || null,
                municipality: this.state.selectedMunicipality || null
            });

            this.state.pois = results.items || [];
            this.renderResultsList(this.state.pois, 'knn');
            this.mapManager.renderPOIs(this.state.pois, true);

            const targetName = knnSubcat 
                ? CONFIG.getSubcategoryMeta(knnSubcat).name 
                : 'Facilities';

            this.updateResultsHeaderCount(results.items.length, `Nearest ${targetName}`);
        } catch (error) {
            console.error('[KNN Error]', error);
            this.showToast('KNN search failed.', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Render Dynamic Category Accordion in Sidebar
     */
    renderCategorySidebar(categoriesTree) {
        const container = document.getElementById('category-accordion');
        if (!container) return;

        let html = '';

        categoriesTree.forEach(cat => {
            const meta = CONFIG.CATEGORIES[cat.category] || {
                icon: 'fa-folder',
                color: '#64748b',
                badgeClass: 'badge-default'
            };

            const subcatListHtml = cat.subcategories.map(sub => {
                const subMeta = CONFIG.getSubcategoryMeta(sub.subcategory);
                return `
                    <div class="subcat-item" data-subcat="${sub.subcategory}">
                        <div class="subcat-left">
                            <i class="fa-solid ${subMeta.icon}" style="color: ${subMeta.color};"></i>
                            <span class="subcat-name">${subMeta.name}</span>
                        </div>
                        <span class="subcat-count">${sub.count.toLocaleString()}</span>
                    </div>
                `;
            }).join('');

            html += `
                <div class="cat-group" data-cat="${cat.category}">
                    <div class="cat-group-header">
                        <div class="cat-title">
                            <span class="cat-icon-box" style="background: ${meta.color}22; color: ${meta.color};">
                                <i class="fa-solid ${meta.icon}"></i>
                            </span>
                            <span class="cat-name-text">${cat.category}</span>
                        </div>
                        <div class="cat-meta-right">
                            <span class="cat-total-badge">${cat.total_count.toLocaleString()}</span>
                            <i class="fa-solid fa-chevron-down cat-arrow"></i>
                        </div>
                    </div>
                    <div class="cat-subcat-list">
                        ${subcatListHtml}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;

        // Add accordion expand/collapse & filter clicks
        container.querySelectorAll('.cat-group-header').forEach(header => {
            header.addEventListener('click', (e) => {
                const group = e.currentTarget.closest('.cat-group');
                group.classList.toggle('expanded');
            });
        });

        container.querySelectorAll('.subcat-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const subcat = e.currentTarget.dataset.subcat;
                
                // Toggle active state
                const wasActive = e.currentTarget.classList.contains('active');
                container.querySelectorAll('.subcat-item').forEach(i => i.classList.remove('active'));
                
                if (!wasActive) {
                    e.currentTarget.classList.add('active');
                    this.state.selectedSubcategory = subcat;
                } else {
                    this.state.selectedSubcategory = '';
                }

                // Synchronize with Radius Selector Dropdown if present
                const radiusSelect = document.getElementById('radius-subcat-select');
                if (radiusSelect) radiusSelect.value = this.state.selectedSubcategory;

                // Ensure origin pin & radius buffer circle are visible on map
                this.mapManager.setQueryCenter(
                    this.state.currentLocation.lat,
                    this.state.currentLocation.lon,
                    this.state.radiusMeters,
                    this.state.currentLocation.label
                );

                // Execute Proximity Radius Search (only returns POIs within selected radius!)
                this.executeRadiusSearch();
                this.mapManager.fitToRadiusCircle();
            });
        });
    }

    /**
     * Populate subcategory dropdown selectors in Radius and KNN tabs
     */
    populateSubcategoryDropdowns(categoriesTree) {
        const radiusSelect = document.getElementById('radius-subcat-select');
        const knnSelect = document.getElementById('knn-subcat-select');

        let optionsHtml = '<option value="">All Categories & Services</option>';
        let knnOptionsHtml = '<option value="">All Facilities</option>';

        categoriesTree.forEach(cat => {
            optionsHtml += `<optgroup label="${cat.category}">`;
            knnOptionsHtml += `<optgroup label="${cat.category}">`;

            cat.subcategories.forEach(sub => {
                const meta = CONFIG.getSubcategoryMeta(sub.subcategory);
                const label = `${meta.displayName || meta.name} (${sub.count})`;
                optionsHtml += `<option value="${sub.subcategory}">${label}</option>`;
                knnOptionsHtml += `<option value="${sub.subcategory}">${label}</option>`;
            });

            optionsHtml += `</optgroup>`;
            knnOptionsHtml += `</optgroup>`;
        });

        if (radiusSelect) {
            radiusSelect.innerHTML = optionsHtml;
            radiusSelect.value = '';
        }

        if (knnSelect) {
            knnSelect.innerHTML = knnOptionsHtml;
            
            // Find and select 'Hospital' option cleanly
            const hospitalOpt = Array.from(knnSelect.options).find(o => o.value.toLowerCase() === 'hospital');
            if (hospitalOpt) {
                knnSelect.value = hospitalOpt.value;
                this.state.selectedSubcategory = hospitalOpt.value;
            }
        }
    }

    /**
     * Render POI Results in Bottom/Side Results List
     */
    renderResultsList(pois, mode) {
        const container = document.getElementById('results-list');
        if (!container) return;

        if (!pois || pois.length === 0) {
            container.innerHTML = `
                <div class="results-empty">
                    <i class="fa-solid fa-map-location-dot"></i>
                    <h4>No facilities found</h4>
                    <p>Try broadening your radius or clearing category filters.</p>
                </div>
            `;
            return;
        }

        let html = '';
        pois.forEach((poi, index) => {
            const meta = CONFIG.getSubcategoryMeta(poi.subcategory);
            const muni = poi.municipality || 'PMC';
            const muniClass = muni === 'PMC' ? 'muni-pmc' : 'muni-pcmc';

            let distHtml = '';
            if (poi.distance_meters !== undefined && poi.distance_meters !== null) {
                const dist = poi.distance_meters < 1000 
                    ? `${Math.round(poi.distance_meters)} m` 
                    : `${(poi.distance_meters / 1000).toFixed(2)} km`;
                distHtml = `<span class="res-dist-tag"><i class="fa-solid fa-route"></i> ${dist}</span>`;
            }

            html += `
                <div class="result-card" data-id="${poi.id}" data-lat="${poi.latitude}" data-lon="${poi.longitude}">
                    <div class="result-card-header">
                        <div class="res-icon" style="background: ${meta.color}22; color: ${meta.color};">
                            <i class="fa-solid ${meta.icon}"></i>
                        </div>
                        <div class="res-title-box">
                            <h4 class="res-name">${poi.name || 'Unnamed Facility'}</h4>
                            <div class="res-meta-line">
                                <span class="res-subcat-badge" style="color: ${meta.color};">${meta.name}</span>
                                <span class="muni-badge ${muniClass}">${muni}</span>
                                ${distHtml}
                            </div>
                        </div>
                    </div>
                    <div class="result-card-body">
                        ${poi.address ? `<div class="res-address"><i class="fa-solid fa-location-dot"></i> ${poi.address}</div>` : ''}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;

        // Card Click -> Pan to Map & Open Popup
        container.querySelectorAll('.result-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const id = parseInt(card.dataset.id, 10);
                const lat = parseFloat(card.dataset.lat);
                const lon = parseFloat(card.dataset.lon);

                container.querySelectorAll('.result-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');

                this.mapManager.focusPOI(id, lat, lon);
            });
        });
    }

    /**
     * Update Results Header Counter Badge
     */
    updateResultsHeaderCount(total, label) {
        const countElem = document.getElementById('results-count-badge');
        const labelElem = document.getElementById('results-label-text');
        if (countElem) countElem.textContent = (total || 0).toLocaleString();
        if (labelElem) labelElem.textContent = label || 'Results';
    }

    // ============================================================
    // GOOGLE-STYLE REAL-TIME SEARCH AUTOCOMPLETE CONTROLLER
    // ============================================================

    /**
     * Setup Real-time Google-Style Autocomplete Search
     */
    setupSearchAutocomplete() {
        const searchInput = document.getElementById('search-input');
        const clearBtn = document.getElementById('search-clear-btn');
        const dropdown = document.getElementById('search-autocomplete-dropdown');

        if (!searchInput || !dropdown) return;

        // 1. Input listener for debounced autocomplete suggestions & background search
        searchInput.addEventListener('input', (e) => {
            const rawVal = e.target.value;
            const query = rawVal.trim();
            this.state.searchQuery = query;

            // Toggle clear button
            if (clearBtn) {
                clearBtn.style.display = rawVal.length > 0 ? 'flex' : 'none';
            }

            if (query.length >= 1) {
                // Debounced autocomplete query (120ms for instant Google-like responsiveness)
                clearTimeout(this.autocompleteDebounceTimer);
                this.autocompleteDebounceTimer = setTimeout(async () => {
                    await this.fetchAndRenderAutocomplete(query);
                }, 120);
            } else {
                this.closeAutocompleteDropdown();
            }

            // Also trigger background active tab filter search
            clearTimeout(this.searchDebounceTimer);
            this.searchDebounceTimer = setTimeout(() => {
                this.triggerActiveTabSearch();
            }, 300);
        });

        // 2. Focus event -> reopen suggestions if search input has text
        searchInput.addEventListener('focus', () => {
            const query = searchInput.value.trim();
            if (query.length >= 1) {
                this.fetchAndRenderAutocomplete(query);
            }
        });

        // 3. Keyboard navigation (ArrowDown, ArrowUp, Enter, Escape)
        searchInput.addEventListener('keydown', (e) => {
            this.handleAutocompleteKeydown(e);
        });

        // 4. Clear button click
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearSearchInput();
            });
        }

        // 5. Click outside -> close autocomplete dropdown
        document.addEventListener('click', (e) => {
            const container = document.getElementById('header-search-container');
            if (container && !container.contains(e.target)) {
                this.closeAutocompleteDropdown();
            }
        });
    }

    /**
     * Fetch suggestions from backend and render into dropdown
     */
    async fetchAndRenderAutocomplete(query) {
        const dropdown = document.getElementById('search-autocomplete-dropdown');
        if (!dropdown) return;

        try {
            const suggestions = await API.getAutocomplete(query, 8);
            this.currentSuggestions = suggestions || [];
            this.selectedSuggestionIndex = -1;
            this.renderAutocompleteDropdown(this.currentSuggestions, query);
        } catch (err) {
            console.warn('[Autocomplete Error]', err);
        }
    }

    /**
     * Render suggestion list inside dropdown
     */
    renderAutocompleteDropdown(suggestions, query) {
        const dropdown = document.getElementById('search-autocomplete-dropdown');
        if (!dropdown) return;

        if (!suggestions || suggestions.length === 0) {
            dropdown.innerHTML = `
                <div class="autocomplete-empty">
                    <i class="fa-solid fa-magnifying-glass"></i>
                    <span>No matching locations found for <strong>"${this.escapeHtml(query)}"</strong></span>
                </div>
            `;
            dropdown.style.display = 'block';
            return;
        }

        let itemsHtml = `
            <div class="autocomplete-header">
                <span>Top Suggestions</span>
                <span class="autocomplete-hints">↑↓ to navigate &bull; ↵ to select</span>
            </div>
        `;

        suggestions.forEach((item, index) => {
            const meta = CONFIG.getSubcategoryMeta(item.subcategory);
            const muni = item.municipality || 'PMC';
            const muniClass = muni === 'PMC' ? 'muni-pmc' : 'muni-pcmc';
            const highlightedName = this.highlightMatch(item.name || 'Unnamed Facility', query);
            const addressSnippet = item.address ? `<span class="autocomplete-addr">• ${this.escapeHtml(item.address.slice(0, 36))}...</span>` : '';

            itemsHtml += `
                <div class="autocomplete-item" data-index="${index}">
                    <div class="autocomplete-icon-box" style="background: ${meta.color}22; color: ${meta.color};">
                        <i class="fa-solid ${meta.icon}"></i>
                    </div>
                    <div class="autocomplete-info">
                        <div class="autocomplete-name">${highlightedName}</div>
                        <div class="autocomplete-meta">
                            <span class="autocomplete-badge" style="color: ${meta.color};">
                                <i class="fa-solid ${meta.icon}"></i> ${meta.name}
                            </span>
                            <span class="autocomplete-muni ${muniClass}">${muni}</span>
                            ${addressSnippet}
                        </div>
                    </div>
                    <i class="fa-solid fa-arrow-right autocomplete-arrow"></i>
                </div>
            `;
        });

        dropdown.innerHTML = itemsHtml;
        dropdown.style.display = 'block';

        // Bind clicks on each suggestion row
        dropdown.querySelectorAll('.autocomplete-item').forEach(el => {
            el.addEventListener('click', (e) => {
                const idx = parseInt(el.dataset.index, 10);
                if (this.currentSuggestions[idx]) {
                    this.selectAutocompleteItem(this.currentSuggestions[idx]);
                }
            });
        });
    }

    /**
     * Highlight matching characters in name safely
     */
    highlightMatch(text, query) {
        if (!text) return '';
        if (!query) return this.escapeHtml(text);

        const safeText = this.escapeHtml(text);
        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(${escapedQuery})`, 'gi');
        return safeText.replace(regex, '<mark class="autocomplete-match">$1</mark>');
    }

    /**
     * Handle Keyboard Navigation (ArrowUp, ArrowDown, Enter, Escape)
     */
    handleAutocompleteKeydown(e) {
        const dropdown = document.getElementById('search-autocomplete-dropdown');
        if (!dropdown || dropdown.style.display === 'none') {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.triggerActiveTabSearch();
            }
            return;
        }

        const items = dropdown.querySelectorAll('.autocomplete-item');
        if (items.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.selectedSuggestionIndex = (this.selectedSuggestionIndex + 1) % items.length;
            this.updateActiveAutocompleteItem(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.selectedSuggestionIndex = (this.selectedSuggestionIndex - 1 + items.length) % items.length;
            this.updateActiveAutocompleteItem(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.selectedSuggestionIndex >= 0 && this.currentSuggestions[this.selectedSuggestionIndex]) {
                this.selectAutocompleteItem(this.currentSuggestions[this.selectedSuggestionIndex]);
            } else {
                this.closeAutocompleteDropdown();
                this.triggerActiveTabSearch();
            }
        } else if (e.key === 'Escape') {
            e.preventDefault();
            this.closeAutocompleteDropdown();
        }
    }

    /**
     * Visual active item update in dropdown during keyboard navigation
     */
    updateActiveAutocompleteItem(items) {
        items.forEach((item, idx) => {
            if (idx === this.selectedSuggestionIndex) {
                item.classList.add('active');
                item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                if (this.currentSuggestions[idx]) {
                    const searchInput = document.getElementById('search-input');
                    if (searchInput) searchInput.value = this.currentSuggestions[idx].name;
                }
            } else {
                item.classList.remove('active');
            }
        });
    }

    /**
     * User clicks or hits Enter on a suggestion
     */
    selectAutocompleteItem(item) {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = item.name;
        }
        this.state.searchQuery = item.name;
        this.closeAutocompleteDropdown();

        // Pan map and open popup
        this.mapManager.focusPOI(item.id, item.latitude, item.longitude, item);

        // Update results list to display selected POI card
        this.state.pois = [item];
        this.renderResultsList(this.state.pois, this.state.activeTab);
        this.updateResultsHeaderCount(1, 'Selected Location');

        // Show toast confirmation
        this.showToast(`Showing: ${item.name}`, 'success');
    }

    /**
     * Clear Search Input and reset results
     */
    clearSearchInput() {
        const searchInput = document.getElementById('search-input');
        const clearBtn = document.getElementById('search-clear-btn');
        if (searchInput) {
            searchInput.value = '';
            searchInput.focus();
        }
        if (clearBtn) {
            clearBtn.style.display = 'none';
        }
        this.state.searchQuery = '';
        this.closeAutocompleteDropdown();
        this.triggerActiveTabSearch();
    }

    /**
     * Close autocomplete dropdown
     */
    closeAutocompleteDropdown() {
        const dropdown = document.getElementById('search-autocomplete-dropdown');
        if (dropdown) {
            dropdown.style.display = 'none';
        }
        this.selectedSuggestionIndex = -1;
    }

    /**
     * Safely escape HTML characters
     */
    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * Reset Filters
     */
    resetFilters() {
        this.clearSearchInput();
        this.state.selectedCategory = '';
        this.state.selectedSubcategory = '';
        this.state.selectedMunicipality = '';

        document.querySelectorAll('.muni-pill').forEach(p => p.classList.toggle('active', p.dataset.muni === ''));
        document.querySelectorAll('.subcat-item').forEach(i => i.classList.remove('active'));

        const radiusSelect = document.getElementById('radius-subcat-select');
        if (radiusSelect) radiusSelect.value = '';

        this.triggerActiveTabSearch();
        this.showToast('Filters reset to default.', 'info');
    }

    /**
     * Update Backend Connection Indicator
     */
    updateHealthBadge(health) {
        const badge = document.getElementById('backend-status-badge');
        if (!badge) return;

        if (health.status === 'healthy' || health.database === 'connected') {
            badge.innerHTML = `<span class="status-dot online"></span> <span class="status-text">Backend Online</span>`;
            badge.title = `Connected to PostgreSQL/PostGIS (smartserve_db)`;
        } else {
            badge.innerHTML = `<span class="status-dot offline"></span> <span class="status-text">Backend Offline</span>`;
            badge.title = `Check FastAPI server`;
        }
    }

    /**
     * Show / Hide Loading Spinner Overlay
     */
    showLoading(isLoading) {
        this.state.isLoading = isLoading;
        const spinner = document.getElementById('global-loader');
        if (spinner) {
            spinner.classList.toggle('active', isLoading);
        }
    }

    /**
     * Show Toast Notification
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast-message toast-${type}`;
        
        let icon = 'fa-info-circle';
        if (type === 'success') icon = 'fa-check-circle';
        if (type === 'warning') icon = 'fa-triangle-exclamation';
        if (type === 'error') icon = 'fa-circle-xmark';

        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 400);
        }, 3500);
    }
}

// Instantiate on DOM Load
document.addEventListener('DOMContentLoaded', () => {
    window.app = new SmartServeApp();
    window.app.init();
});

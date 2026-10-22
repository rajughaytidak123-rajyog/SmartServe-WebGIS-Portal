/**
 * SmartServe GIS - Spatial Analytics & Chart Manager
 * Utilizes Chart.js to render spatial distributions, POI density, and municipal comparisons.
 */

class AnalyticsManager {
    constructor() {
        this.categoryChart = null;
        this.muniChart = null;
        this.densityChart = null;
        this.topServicesChart = null;
    }

    /**
     * Fetch analytics data and initialize all dashboard charts
     */
    async loadAndRender() {
        try {
            const [overview, densityData] = await Promise.all([
                API.getAnalyticsOverview(),
                API.getDensityMetrics()
            ]);

            this.updateKpiCards(overview, densityData);
            this.renderMunicipalShareChart(overview.municipal_breakdown);
            this.renderCategoryChart(overview.category_breakdown);
            this.renderDensityChart(densityData.densities);
            this.renderTopServicesChart(overview.top_subcategories);
        } catch (error) {
            console.error('[Analytics Error] Failed to load analytics data:', error);
        }
    }

    /**
     * Update Dashboard KPI summary cards
     */
    updateKpiCards(overview, densityData) {
        const totalPoisElem = document.getElementById('kpi-total-pois');
        const totalCatsElem = document.getElementById('kpi-total-cats');
        const pmcPoisElem = document.getElementById('kpi-pmc-pois');
        const pcmcPoisElem = document.getElementById('kpi-pcmc-pois');

        if (totalPoisElem) totalPoisElem.textContent = overview.total_services.toLocaleString();
        if (totalCatsElem) totalCatsElem.textContent = overview.total_categories || 20;

        const pmcCount = overview.municipal_breakdown?.PMC || 0;
        const pcmcCount = overview.municipal_breakdown?.PCMC || 0;

        if (pmcPoisElem) pmcPoisElem.textContent = `${pmcCount.toLocaleString()} (${Math.round((pmcCount / overview.total_services) * 100)}%)`;
        if (pcmcPoisElem) pcmcPoisElem.textContent = `${pcmcCount.toLocaleString()} (${Math.round((pcmcCount / overview.total_services) * 100)}%)`;
    }

    /**
     * PMC vs PCMC Municipal Share Doughnut Chart
     */
    renderMunicipalShareChart(breakdown = {}) {
        const ctx = document.getElementById('chart-muni-share');
        if (!ctx) return;

        if (this.muniChart) this.muniChart.destroy();

        const labels = Object.keys(breakdown);
        const data = Object.values(breakdown);

        this.muniChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels.map(l => l === 'PMC' ? 'Pune (PMC)' : 'Pimpri-Chinchwad (PCMC)'),
                datasets: [{
                    data: data,
                    backgroundColor: ['#0984e3', '#00b894'],
                    borderColor: '#131c31',
                    borderWidth: 2.5,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { family: 'Inter', size: 12, weight: 600 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` ${ctx.label}: ${ctx.raw.toLocaleString()} facilities`
                        }
                    }
                },
                cutout: '65%'
            }
        });
    }

    /**
     * Category Distribution Bar Chart
     */
    renderCategoryChart(categories = []) {
        const ctx = document.getElementById('chart-categories');
        if (!ctx) return;

        if (this.categoryChart) this.categoryChart.destroy();

        const labels = categories.map(c => c.category);
        const counts = categories.map(c => c.count);
        const colors = categories.map(c => {
            const cat = CONFIG.CATEGORIES[c.category];
            return cat ? cat.color : '#38bdf8';
        });

        this.categoryChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Number of POIs',
                    data: counts,
                    backgroundColor: colors.map(c => `${c}dd`),
                    borderColor: colors,
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` Facilities: ${ctx.raw.toLocaleString()}`
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11, weight: 600 } },
                        grid: { display: false }
                    },
                    y: {
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } },
                        grid: { color: 'rgba(255, 255, 255, 0.06)' }
                    }
                }
            }
        });
    }

    /**
     * Spatial Density (POIs per km²) Comparison Bar Chart
     */
    renderDensityChart(densities = []) {
        const ctx = document.getElementById('chart-density');
        if (!ctx) return;

        if (this.densityChart) this.densityChart.destroy();

        const labels = densities.map(d => `${d.name} (${d.code})`);
        const densityValues = densities.map(d => d.density_per_sqkm);

        this.densityChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'POIs per km²',
                    data: densityValues,
                    backgroundColor: ['#0984e3dd', '#00b894dd'],
                    borderColor: ['#0984e3', '#00b894'],
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` Density: ${ctx.raw} POIs / km²`
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } },
                        grid: { color: 'rgba(255, 255, 255, 0.06)' },
                        title: { display: true, text: 'Facilities per km²', color: '#94a3b8', font: { weight: 600 } }
                    },
                    y: {
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11, weight: 600 } },
                        grid: { display: false }
                    }
                }
            }
        });
    }

    /**
     * Top 5 Subcategories Horizontal Bar Chart
     */
    renderTopServicesChart(topSubcats = []) {
        const ctx = document.getElementById('chart-top-services');
        if (!ctx) return;

        if (this.topServicesChart) this.topServicesChart.destroy();

        const labels = topSubcats.map(s => {
            const meta = CONFIG.getSubcategoryMeta(s.subcategory);
            return meta.name;
        });
        const counts = topSubcats.map(s => s.count);

        this.topServicesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Count',
                    data: counts,
                    backgroundColor: '#8b5cf6cc',
                    borderColor: '#8b5cf6',
                    borderWidth: 1.5,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } },
                        grid: { color: '#334155' }
                    },
                    y: {
                        ticks: { color: '#94a3b8', font: { family: 'Inter', size: 11 } },
                        grid: { display: false }
                    }
                }
            }
        });
    }
}

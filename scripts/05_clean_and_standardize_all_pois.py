"""
SmartServe GIS - Phase 4: Multi-Service POI Cleaning, Standardization & Final Consolidation
Script: scripts/05_clean_and_standardize_all_pois.py

Goal:
1. Process all 18 raw POI datasets from Phase 3.
2. Perform geometric validation, spatial point-in-polygon filtering, PMC/PCMC classification,
   and intelligent deduplication.
3. Standardize schema into a unified relational model.
4. Save:
   - data/cleaned/<slug>.geojson (18 separate clean layers)
   - data/final/all_services.geojson (Consolidated master dataset ready for PostGIS)
5. Generate an interactive multi-category Leaflet WebGIS viewer.
"""

import os
import sys
import io
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# -------------------------------------------------------------
# 1. SETUP DIRECTORIES & BOUNDARIES
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
CLEANED_DIR = os.path.join(BASE_DIR, "data", "cleaned")
FINAL_DIR = os.path.join(BASE_DIR, "data", "final")
BOUNDARY_DIR = os.path.join(BASE_DIR, "data", "boundary")

for d in [CLEANED_DIR, FINAL_DIR]:
    os.makedirs(d, exist_ok=True)

gdf_municipalities = gpd.read_file(os.path.join(BOUNDARY_DIR, "pmc_pcmc_combined.geojson"))

# Category list matching Phase 3 definitions
SERVICE_CATEGORIES = [
    {"category": "Healthcare", "subcategory": "Hospital", "slug": "hospitals", "icon": "🏥"},
    {"category": "Healthcare", "subcategory": "Clinic", "slug": "clinics", "icon": "🩺"},
    {"category": "Healthcare", "subcategory": "Pharmacy", "slug": "pharmacies", "icon": "💊"},
    {"category": "Food", "subcategory": "Restaurant", "slug": "restaurants", "icon": "🍔"},
    {"category": "Food", "subcategory": "Cafe", "slug": "cafes", "icon": "☕"},
    {"category": "Food", "subcategory": "Bakery", "slug": "bakeries", "icon": "🥐"},
    {"category": "Transport", "subcategory": "Petrol Pump", "slug": "petrol_pumps", "icon": "⛽"},
    {"category": "Transport", "subcategory": "EV Charging", "slug": "ev_charging", "icon": "🔋"},
    {"category": "Transport", "subcategory": "Metro Station", "slug": "metro_stations", "icon": "🚇"},
    {"category": "Transport", "subcategory": "Bus Station", "slug": "bus_stations", "icon": "🚌"},
    {"category": "Accommodation", "subcategory": "Hotel", "slug": "hotels", "icon": "🏨"},
    {"category": "Finance", "subcategory": "ATM", "slug": "atms", "icon": "🏧"},
    {"category": "Finance", "subcategory": "Bank", "slug": "banks", "icon": "🏦"},
    {"category": "Emergency", "subcategory": "Police Station", "slug": "police_stations", "icon": "👮"},
    {"category": "Emergency", "subcategory": "Fire Station", "slug": "fire_stations", "icon": "🚒"},
    {"category": "Education", "subcategory": "School", "slug": "schools", "icon": "🏫"},
    {"category": "Education", "subcategory": "College", "slug": "colleges", "icon": "🎓"},
    {"category": "Shopping", "subcategory": "Shopping Mall", "slug": "shopping_malls", "icon": "🛍️"},
    {"category": "Shopping", "subcategory": "Supermarket", "slug": "supermarkets", "icon": "🛒"},
    {"category": "Recreation", "subcategory": "Park", "slug": "parks", "icon": "🌳"}
]

# -------------------------------------------------------------
# 2. STRING & ATTRIBUTE SANITIZERS
# -------------------------------------------------------------
def format_address(row: pd.Series, municipality_name: str) -> str:
    parts = []
    street = row.get("addr_street")
    suburb = row.get("addr_suburb")
    city = row.get("addr_city")
    postcode = row.get("addr_postcode")
    
    if street and str(street).strip() and str(street).strip().lower() != "nan":
        parts.append(str(street).strip())
    if suburb and str(suburb).strip() and str(suburb).strip().lower() != "nan":
        parts.append(str(suburb).strip())
    if city and str(city).strip() and str(city).strip().lower() != "nan":
        parts.append(str(city).strip())
    elif municipality_name:
        parts.append(municipality_name)
    if postcode and str(postcode).strip() and str(postcode).strip().lower() != "nan":
        parts.append(str(postcode).strip())
        
    if not parts:
        return f"{municipality_name}, Maharashtra"
    return ", ".join(parts)


def clean_phone(phone_raw: str) -> str:
    if not phone_raw or pd.isna(phone_raw):
        return None
    val = str(phone_raw).strip()
    if val.lower() in ["nan", "none", "null", ""]:
        return None
    return val.replace(";", ", ")


def clean_url(url_raw: str) -> str:
    if not url_raw or pd.isna(url_raw):
        return None
    val = str(url_raw).strip()
    if val.lower() in ["nan", "none", "null", ""]:
        return None
    if not val.startswith("http://") and not val.startswith("https://"):
        val = "https://" + val
    return val


def clean_text_field(text_raw: str) -> str:
    if not text_raw or pd.isna(text_raw):
        return None
    val = str(text_raw).strip()
    if val.lower() in ["nan", "none", "null", ""]:
        return None
    return val

# -------------------------------------------------------------
# 3. CLEANING ENGINE FOR A SINGLE CATEGORY
# -------------------------------------------------------------
def clean_single_service(category_meta: dict) -> tuple:
    slug = category_meta["slug"]
    category = category_meta["category"]
    subcategory = category_meta["subcategory"]
    raw_path = os.path.join(RAW_DIR, f"{slug}.geojson")
    
    if not os.path.exists(raw_path):
        print(f"  [WARN] Missing raw file for {slug}. Skipping.")
        return None, None
        
    gdf_raw = gpd.read_file(raw_path)
    total_raw = len(gdf_raw)
    
    if total_raw == 0:
        print(f"  [WARN] Empty dataset for {slug}.")
        return None, None
        
    # CRS verification
    if gdf_raw.crs is None or gdf_raw.crs.to_epsg() != 4326:
        gdf_raw = gdf_raw.set_crs(epsg=4326, allow_override=True)
        
    # Valid geometry filter
    valid_mask = gdf_raw.geometry.is_valid & (~gdf_raw.geometry.is_empty) & (gdf_raw.geometry.geom_type == "Point")
    gdf_valid = gdf_raw[valid_mask].copy()
    
    # Point-in-polygon with PMC / PCMC
    gdf_joined = gpd.sjoin(
        gdf_valid, 
        gdf_municipalities[["municipality", "municipality_name", "geometry"]], 
        how="inner", 
        predicate="within"
    )
    outside_study_area = len(gdf_valid) - len(gdf_joined)
    
    # Deduplication
    gdf_dedup = gdf_joined.drop_duplicates(subset=["osm_id"]).copy()
    
    # Proximity deduplication
    gdf_utm = gdf_dedup.to_crs(epsg=32643)
    to_keep = []
    seen = set()
    for idx, row in gdf_utm.iterrows():
        raw_name = str(row.get("name") or row.get("name_en") or "").strip().lower()
        if not raw_name or raw_name in ["nan", "none"]:
            to_keep.append(idx)
            continue
        geom = row.geometry
        nearby = gdf_utm[
            (gdf_utm.index != idx) & 
            (gdf_utm.geometry.distance(geom) < 20.0) & 
            (gdf_utm["name"].str.strip().str.lower() == raw_name)
        ]
        pair_key = tuple(sorted([idx] + list(nearby.index)))
        if pair_key not in seen:
            seen.add(pair_key)
            to_keep.append(idx)
            
    gdf_cleaned = gdf_dedup.loc[to_keep].copy()
    
    # Standardize attributes
    records = []
    missing_name_count = 0
    for _, row in gdf_cleaned.iterrows():
        name = row.get("name") or row.get("name_en")
        if not name or str(name).strip().lower() in ["nan", "none", "null", ""]:
            brand = clean_text_field(row.get("brand"))
            operator = clean_text_field(row.get("operator"))
            if brand:
                name = f"{brand} {subcategory}"
            elif operator:
                name = f"{operator} {subcategory}"
            else:
                name = f"Unnamed {subcategory}"
            missing_name_count += 1
        else:
            name = str(name).strip()
            
        lat = round(float(row.geometry.y), 6)
        lon = round(float(row.geometry.x), 6)
        muni_code = row.get("municipality", "PMC")
        muni_name = row.get("municipality_name", "Pune Municipal Corporation")
        
        records.append({
            "name": name,
            "category": category,
            "subcategory": subcategory,
            "latitude": lat,
            "longitude": lon,
            "address": format_address(row, muni_name),
            "phone": clean_phone(row.get("phone")),
            "website": clean_url(row.get("website")),
            "opening_hours": clean_text_field(row.get("opening_hours")),
            "operator": clean_text_field(row.get("operator")),
            "brand": clean_text_field(row.get("brand")),
            "wheelchair": clean_text_field(row.get("wheelchair")),
            "municipality": muni_code,
            "osm_id": f"{row.get('osm_type', 'node')}_{row.get('osm_id')}",
            "source": "OpenStreetMap",
            "geometry": Point(lon, lat)
        })
        
    gdf_final_cat = gpd.GeoDataFrame(records, crs="EPSG:4326")
    
    # Save individual cleaned GeoJSON
    clean_cat_path = os.path.join(CLEANED_DIR, f"{slug}.geojson")
    gdf_final_cat.to_file(clean_cat_path, driver="GeoJSON")
    
    stats = {
        "category": category,
        "subcategory": subcategory,
        "slug": slug,
        "raw_count": total_raw,
        "outside_bounds": outside_study_area,
        "duplicates_removed": total_raw - outside_study_area - len(gdf_final_cat),
        "clean_count": len(gdf_final_cat),
        "pmc_count": int((gdf_final_cat["municipality"] == "PMC").sum()),
        "pcmc_count": int((gdf_final_cat["municipality"] == "PCMC").sum()),
        "with_phone": int(gdf_final_cat["phone"].notna().sum()),
        "with_website": int(gdf_final_cat["website"].notna().sum())
    }
    return gdf_final_cat, stats

# -------------------------------------------------------------
# 4. EXECUTE PIPELINE ACROSS ALL 20 CATEGORIES
# -------------------------------------------------------------
print("=" * 70)
print("  SMARTSERVE GIS - PHASE 4: DATA CLEANING & STANDARDIZATION")
print("=" * 70)

all_cleaned_gdfs = []
quality_reports = []

for sdef in SERVICE_CATEGORIES:
    gdf_cat, stats = clean_single_service(sdef)
    if gdf_cat is not None and len(gdf_cat) > 0:
        all_cleaned_gdfs.append(gdf_cat)
        quality_reports.append(stats)
        print(f"  ✓ {stats['category']:<14} | {stats['subcategory']:<18} -> {stats['clean_count']:>4} POIs (PMC: {stats['pmc_count']}, PCMC: {stats['pcmc_count']})")

# -------------------------------------------------------------
# 5. CONSOLIDATE MASTER DATASET
# -------------------------------------------------------------
gdf_all_services = gpd.GeoDataFrame(
    pd.concat(all_cleaned_gdfs, ignore_index=True),
    crs="EPSG:4326"
)

# Assign a sequential master ID (1-indexed for SQL Primary Key compatibility)
gdf_all_services.insert(0, "id", range(1, len(gdf_all_services) + 1))

# Export Master GeoJSON
master_geojson_path = os.path.join(FINAL_DIR, "all_services.geojson")
gdf_all_services.to_file(master_geojson_path, driver="GeoJSON")
print(f"\n[SUCCESS] Consolidated Master POI Dataset ({len(gdf_all_services)} total POIs) -> {master_geojson_path}")

# Save Quality Report
report_path = os.path.join(CLEANED_DIR, "all_services_quality_report.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump({
        "total_pois": len(gdf_all_services),
        "total_pmc": int((gdf_all_services["municipality"] == "PMC").sum()),
        "total_pcmc": int((gdf_all_services["municipality"] == "PCMC").sum()),
        "categories_breakdown": quality_reports
    }, f, indent=2)

# -------------------------------------------------------------
# 6. TABULAR SUMMARY AUDIT
# -------------------------------------------------------------
print("\n" + "=" * 70)
print(f"{'Category':<14} | {'Subcategory':<18} | {'PMC':<6} | {'PCMC':<6} | {'Total':<6}")
print("-" * 70)
for r in quality_reports:
    print(f"{r['category']:<14} | {r['subcategory']:<18} | {r['pmc_count']:<6} | {r['pcmc_count']:<6} | {r['clean_count']:<6}")
print("-" * 70)
print(f"{'TOTAL SERVICES':<35} | {int((gdf_all_services['municipality']=='PMC').sum()):<6} | {int((gdf_all_services['municipality']=='PCMC').sum()):<6} | {len(gdf_all_services):<6}")
print("=" * 70)

# -------------------------------------------------------------
# 7. GENERATE MULTI-SERVICE INTERACTIVE LEAFLET WEB PORTAL
# -------------------------------------------------------------
leaflet_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SmartServe GIS — Multi-Service Spatial Portal (Pune & PCMC)</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    body, html {{ height: 100%; width: 100%; overflow: hidden; display: flex; flex-direction: column; }}
    
    header {{
      background: #1a365d; color: white; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 2px 10px rgba(0,0,0,0.2); z-index: 1001;
    }}
    header h1 {{ font-size: 18px; font-weight: 700; display: flex; align-items: center; gap: 8px; }}
    header .badge {{ background: #3182ce; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
    
    #container {{ display: flex; flex: 1; position: relative; }}
    #sidebar {{
      width: 340px; background: #ffffff; border-right: 1px solid #e2e8f0; display: flex; flex-direction: column; z-index: 1000; box-shadow: 2px 0 10px rgba(0,0,0,0.05);
    }}
    .sidebar-header {{ padding: 16px; border-bottom: 1px solid #edf2f7; background: #f8fafc; }}
    .search-box {{
      width: 100%; padding: 10px 14px; border: 1.5px solid #cbd5e0; border-radius: 8px; font-size: 13.5px; outline: none; transition: border-color 0.2s;
    }}
    .search-box:focus {{ border-color: #3182ce; }}
    
    .category-filter {{
      margin-top: 10px; width: 100%; padding: 9px 12px; border: 1.5px solid #cbd5e0; border-radius: 8px; font-size: 13px; background: white; outline: none;
    }}
    
    .stats-summary {{ padding: 12px 16px; background: #ebf8ff; border-bottom: 1px solid #bee3f8; font-size: 12.5px; color: #2b6cb0; display: flex; justify-content: space-between; }}
    
    #results-list {{ flex: 1; overflow-y: auto; padding: 10px; }}
    .service-card {{
      background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 8px; cursor: pointer; transition: all 0.2s;
    }}
    .service-card:hover {{ border-color: #3182ce; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.06); }}
    .service-card h3 {{ font-size: 14px; color: #1a202c; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }}
    .service-card .cat-tag {{ display: inline-block; font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #edf2f7; color: #4a5568; font-weight: 500; margin-bottom: 6px; }}
    .service-card .addr {{ font-size: 12px; color: #718096; line-height: 1.35; }}
    
    #map {{ flex: 1; height: 100%; }}
  </style>
</head>
<body>

  <header>
    <h1>🗺️ SmartServe GIS</h1>
    <div>
      <span class="badge">Study Area: Pune + PCMC</span>
      <span class="badge" style="background:#2b6cb0; margin-left:6px;">{len(gdf_all_services)} POIs Loaded</span>
    </div>
  </header>

  <div id="container">
    <div id="sidebar">
      <div class="sidebar-header">
        <input type="text" id="searchInput" class="search-box" placeholder="🔍 Search service by name..." />
        <select id="categorySelect" class="category-filter">
          <option value="ALL">🌟 All Categories ({len(gdf_all_services)})</option>
          <option value="Healthcare">🏥 Healthcare</option>
          <option value="Food">🍔 Food & Dining</option>
          <option value="Transport">🚗 Transport & Fuel</option>
          <option value="Finance">🏧 Finance & Banking</option>
          <option value="Education">🏫 Education</option>
          <option value="Emergency">🚨 Emergency Services</option>
          <option value="Shopping">🛍️ Shopping</option>
          <option value="Accommodation">🏨 Accommodation</option>
          <option value="Recreation">🌳 Recreation & Parks</option>
        </select>
      </div>
      <div class="stats-summary">
        <span>Showing: <strong id="shownCount">{len(gdf_all_services)}</strong> services</span>
        <span>PMC: <strong>{int((gdf_all_services['municipality']=='PMC').sum())}</strong> | PCMC: <strong>{int((gdf_all_services['municipality']=='PCMC').sum())}</strong></span>
      </div>
      <div id="results-list"></div>
    </div>
    <div id="map"></div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
  <script>
    const map = L.map('map').setView([18.55, 73.85], 11);
    
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }}).addTo(map);

    // Boundary overlay
    fetch('../boundary/pmc_pcmc_combined.geojson')
      .then(r => r.json())
      .then(bData => {{
        L.geoJSON(bData, {{
          style: f => ({{
            color: f.properties.municipality === 'PMC' ? '#2b6cb0' : '#276749',
            weight: 2,
            fillColor: f.properties.municipality === 'PMC' ? '#3182ce' : '#38a169',
            fillOpacity: 0.1
          }})
        }}).addTo(map);
      }});

    const iconMap = {{
      'Hospital': '🏥', 'Clinic': '🩺', 'Pharmacy': '💊',
      'Restaurant': '🍔', 'Cafe': '☕', 'Bakery': '🥐',
      'Petrol Pump': '⛽', 'EV Charging': '🔋', 'Metro Station': '🚇', 'Bus Station': '🚌',
      'Hotel': '🏨', 'ATM': '🏧', 'Bank': '🏦',
      'Police Station': '👮', 'Fire Station': '🚒',
      'School': '🏫', 'College': '🎓',
      'Shopping Mall': '🛍️', 'Supermarket': '🛒',
      'Park': '🌳'
    }};

    let allFeatures = [];
    const markerCluster = L.markerClusterGroup({{ maxClusterRadius: 40 }});
    map.addLayer(markerCluster);

    const markersById = {{}};

    fetch('../final/all_services.geojson')
      .then(r => r.json())
      .then(data => {{
        allFeatures = data.features;
        renderMapAndList(allFeatures);
      }});

    function renderMapAndList(features) {{
      markerCluster.clearLayers();
      const listContainer = document.getElementById('results-list');
      listContainer.innerHTML = '';
      document.getElementById('shownCount').innerText = features.length;

      features.forEach(f => {{
        const p = f.properties;
        const icon = iconMap[p.subcategory] || '📍';
        const latlng = [f.geometry.coordinates[1], f.geometry.coordinates[0]];

        const marker = L.circleMarker(latlng, {{
          radius: 6,
          fillColor: '#3182ce',
          color: '#ffffff',
          weight: 1.5,
          fillOpacity: 0.85
        }});

        marker.bindPopup(`
          <div style="font-size:13px; line-height:1.45;">
            <h4 style="margin:0 0 4px 0; color:#2b6cb0;">${{icon}} ${{p.name}}</h4>
            <strong>Category:</strong> ${{p.category}} (${{p.subcategory}})<br>
            <strong>Municipality:</strong> ${{p.municipality}}<br>
            <strong>Address:</strong> ${{p.address || 'N/A'}}<br>
            ${{p.phone ? `<strong>Phone:</strong> ${{p.phone}}<br>` : ''}}
            ${{p.website ? `<strong>Website:</strong> <a href="${{p.website}}" target="_blank">Visit Web</a><br>` : ''}}
            ${{p.opening_hours ? `<strong>Hours:</strong> ${{p.opening_hours}}<br>` : ''}}
            <small style="color:#a0aec0;">ID: #${{p.id}} | OSM: ${{p.osm_id}}</small>
          </div>
        `);

        markerCluster.addLayer(marker);
        markersById[p.id] = marker;

        // Render card
        const card = document.createElement('div');
        card.className = 'service-card';
        card.innerHTML = `
          <h3>${{icon}} ${{p.name}}</h3>
          <div><span class="cat-tag">${{p.subcategory}}</span> <span class="cat-tag" style="background:#ebf8ff; color:#2b6cb0;">${{p.municipality}}</span></div>
          <div class="addr">${{p.address}}</div>
        `;
        card.onclick = () => {{
          map.setView(latlng, 16);
          marker.openPopup();
        }};
        listContainer.appendChild(card);
      }});
    }}

    // Filter handlers
    function applyFilters() {{
      const query = document.getElementById('searchInput').value.toLowerCase().trim();
      const selectedCat = document.getElementById('categorySelect').value;

      const filtered = allFeatures.filter(f => {{
        const p = f.properties;
        const matchesQuery = !query || p.name.toLowerCase().includes(query) || (p.address && p.address.toLowerCase().includes(query));
        const matchesCat = (selectedCat === 'ALL') || (p.category === selectedCat);
        return matchesQuery && matchesCat;
      }});

      renderMapAndList(filtered);
    }}

    document.getElementById('searchInput').addEventListener('input', applyFilters);
    document.getElementById('categorySelect').addEventListener('change', applyFilters);
  </script>
</body>
</html>
"""

html_out_path = os.path.join(CLEANED_DIR, "all_services_inspection_map.html")
with open(html_out_path, "w", encoding="utf-8") as f:
    f.write(leaflet_html)

print(f"[SUCCESS] Generated Multi-Service Interactive WebGIS App -> {html_out_path}\n")

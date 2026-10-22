"""
SmartServe GIS - Phase 2: Data Cleaning, Standardization & Spatial Validation
Script: scripts/03_clean_and_standardize_pois.py

Goal:
1. Load raw POI GeoJSONs (hospitals, restaurants, petrol pumps).
2. Validate CRS (EPSG:4326) and 2D Point geometries.
3. Perform spatial Point-in-Polygon mask filter against PMC and PCMC boundaries.
4. Spatially classify every POI with municipality ('PMC' vs 'PCMC').
5. Detect and remove duplicate records.
6. Clean and standardize attributes (name, address, phone, website, opening hours).
7. Save cleaned GeoJSON files in data/cleaned/:
   - data/cleaned/hospitals.geojson
   - data/cleaned/restaurants.geojson
   - data/cleaned/petrol_pumps.geojson
8. Generate a comprehensive Data Quality Report and interactive Leaflet map.
"""

import os
import sys
import io
import json
import re
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# -------------------------------------------------------------
# 1. SETUP DIRECTORIES & BOUNDARIES
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
CLEANED_DIR = os.path.join(BASE_DIR, "data", "cleaned")
BOUNDARY_DIR = os.path.join(BASE_DIR, "data", "boundary")
os.makedirs(CLEANED_DIR, exist_ok=True)

# Load boundary layers
combined_boundary_path = os.path.join(BOUNDARY_DIR, "pmc_pcmc_combined.geojson")
study_area_path = os.path.join(BOUNDARY_DIR, "study_area.geojson")

gdf_municipalities = gpd.read_file(combined_boundary_path)
gdf_study_area = gpd.read_file(study_area_path)
study_area_polygon = gdf_study_area.geometry.iloc[0]

# -------------------------------------------------------------
# 2. HELPER FUNCTIONS FOR CLEANING & ADDRESS FORMATTING
# -------------------------------------------------------------
def format_address(row: pd.Series, municipality_name: str) -> str:
    """Constructs a clean human-readable address from available OSM address tags."""
    parts = []
    
    street = row.get("addr_street")
    suburb = row.get("addr_suburb")
    city = row.get("addr_city")
    postcode = row.get("addr_postcode")
    
    if street and str(street).strip() and str(street).strip().lower() != "nan":
        parts.append(str(street).strip())
    if suburb and str(suburb).strip() and str(suburb).strip().lower() != "nan":
        parts.append(str(suburb).strip())
    
    # Add city / municipality context
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
    """Normalizes phone string if present."""
    if not phone_raw or pd.isna(phone_raw):
        return None
    val = str(phone_raw).strip()
    if val.lower() in ["nan", "none", "null", ""]:
        return None
    # Format standard separator if multiple numbers exist
    val = val.replace(";", ", ")
    return val


def clean_url(url_raw: str) -> str:
    """Normalizes website URL."""
    if not url_raw or pd.isna(url_raw):
        return None
    val = str(url_raw).strip()
    if val.lower() in ["nan", "none", "null", ""]:
        return None
    if not val.startswith("http://") and not val.startswith("https://"):
        val = "https://" + val
    return val


def clean_text_field(text_raw: str) -> str:
    """Clean generic string fields."""
    if not text_raw or pd.isna(text_raw):
        return None
    val = str(text_raw).strip()
    if val.lower() in ["nan", "none", "null", ""]:
        return None
    return val

# -------------------------------------------------------------
# 3. CORE POI CLEANING PIPELINE FUNCTION
# -------------------------------------------------------------
def clean_poi_dataset(raw_filename: str, clean_filename: str, default_category: str, default_subcategory: str) -> dict:
    """
    Cleans, validates, clips to study area, assigns municipality,
    deduplicates, and exports standardized GeoJSON.
    """
    raw_path = os.path.join(RAW_DIR, raw_filename)
    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Raw file not found: {raw_path}")
        
    print(f"\n[INFO] Processing Category: {default_category} -> {default_subcategory} ({raw_filename})...")
    gdf_raw = gpd.read_file(raw_path)
    total_raw = len(gdf_raw)
    
    # 1. CRS validation
    if gdf_raw.crs is None or gdf_raw.crs.to_epsg() != 4326:
        gdf_raw = gdf_raw.set_crs(epsg=4326, allow_override=True)
        
    # 2. Geometry validity & missing coordinates
    valid_mask = gdf_raw.geometry.is_valid & (~gdf_raw.geometry.is_empty) & (gdf_raw.geometry.geom_type == "Point")
    gdf_valid = gdf_raw[valid_mask].copy()
    invalid_geoms_count = total_raw - len(gdf_valid)
    
    # 3. Spatial Join with Municipality Boundary (PMC vs PCMC point-in-polygon)
    # Using spatial join predicate 'within'
    gdf_joined = gpd.sjoin(
        gdf_valid, 
        gdf_municipalities[["municipality", "municipality_name", "geometry"]], 
        how="inner", 
        predicate="within"
    )
    
    outside_study_area_count = len(gdf_valid) - len(gdf_joined)
    
    # 4. Duplicate removal (Exact OSM ID match)
    initial_joined_count = len(gdf_joined)
    gdf_dedup = gdf_joined.drop_duplicates(subset=["osm_id"]).copy()
    osm_id_duplicates = initial_joined_count - len(gdf_dedup)
    
    # Proximity deduplication (points of same name within 20 meters)
    # Project temporarily to UTM Zone 43N (meters) for accurate metric distance check
    gdf_utm = gdf_dedup.to_crs(epsg=32643)
    to_keep = []
    seen = set()
    
    for idx, row in gdf_utm.iterrows():
        raw_name = str(row.get("name") or row.get("name_en") or "").strip().lower()
        if not raw_name or raw_name in ["nan", "none"]:
            to_keep.append(idx)
            continue
            
        geom = row.geometry
        # Find points with exact same name within 20m buffer
        nearby = gdf_utm[
            (gdf_utm.index != idx) & 
            (gdf_utm.geometry.distance(geom) < 20.0) & 
            (gdf_utm["name"].str.strip().str.lower() == raw_name)
        ]
        
        pair_key = tuple(sorted([idx] + list(nearby.index)))
        if pair_key not in seen:
            seen.add(pair_key)
            to_keep.append(idx)
            
    gdf_cleaned_spatial = gdf_dedup.loc[to_keep].copy()
    spatial_duplicates = len(gdf_dedup) - len(gdf_cleaned_spatial)
    
    # 5. Schema Normalization & Attribute Standardization
    cleaned_rows = []
    missing_name_count = 0
    
    for _, row in gdf_cleaned_spatial.iterrows():
        name = row.get("name") or row.get("name_en")
        if not name or str(name).strip().lower() in ["nan", "none", "null", ""]:
            # Meaningful fallback name
            operator_name = clean_text_field(row.get("operator"))
            brand_name = clean_text_field(row.get("brand"))
            if brand_name:
                name = f"{brand_name} {default_subcategory}"
            elif operator_name:
                name = f"{operator_name} {default_subcategory}"
            else:
                name = f"Unnamed {default_subcategory}"
            missing_name_count += 1
        else:
            name = str(name).strip()
            
        lat = round(float(row.geometry.y), 6)
        lon = round(float(row.geometry.x), 6)
        
        muni_code = row.get("municipality", "PMC")
        muni_name = row.get("municipality_name", "Pune Municipal Corporation")
        
        address = format_address(row, muni_name)
        phone = clean_phone(row.get("phone"))
        website = clean_url(row.get("website"))
        opening_hours = clean_text_field(row.get("opening_hours"))
        operator_val = clean_text_field(row.get("operator"))
        brand_val = clean_text_field(row.get("brand"))
        wheelchair_val = clean_text_field(row.get("wheelchair"))
        emergency_val = clean_text_field(row.get("emergency"))
        
        cleaned_rows.append({
            "name": name,
            "category": default_category,
            "subcategory": default_subcategory,
            "latitude": lat,
            "longitude": lon,
            "address": address,
            "phone": phone,
            "website": website,
            "opening_hours": opening_hours,
            "operator": operator_val,
            "brand": brand_val,
            "wheelchair": wheelchair_val,
            "emergency": emergency_val,
            "municipality": muni_code,
            "osm_id": f"{row.get('osm_type', 'node')}_{row.get('osm_id')}",
            "source": "OpenStreetMap",
            "geometry": Point(lon, lat)
        })
        
    gdf_final = gpd.GeoDataFrame(cleaned_rows, crs="EPSG:4326")
    
    # 6. Save Cleaned GeoJSON
    clean_path = os.path.join(CLEANED_DIR, clean_filename)
    gdf_final.to_file(clean_path, driver="GeoJSON")
    print(f"       -> [SUCCESS] Saved cleaned dataset ({len(gdf_final)} POIs) -> {clean_path}")
    
    # Quality metrics summary dictionary
    pmc_count = len(gdf_final[gdf_final["municipality"] == "PMC"])
    pcmc_count = len(gdf_final[gdf_final["municipality"] == "PCMC"])
    
    report = {
        "category": default_category,
        "subcategory": default_subcategory,
        "raw_records": total_raw,
        "invalid_geometries": invalid_geoms_count,
        "outside_study_area_removed": outside_study_area_count,
        "duplicate_records_removed": osm_id_duplicates + spatial_duplicates,
        "missing_names_handled": missing_name_count,
        "final_valid_records": len(gdf_final),
        "pmc_records": pmc_count,
        "pcmc_records": pcmc_count,
        "records_with_phone": int(gdf_final["phone"].notna().sum()),
        "records_with_website": int(gdf_final["website"].notna().sum()),
        "records_with_opening_hours": int(gdf_final["opening_hours"].notna().sum())
    }
    return report

# -------------------------------------------------------------
# 4. EXECUTE CLEANING FOR 3 CORE SERVICES
# -------------------------------------------------------------
print("=" * 65)
print("  SMARTSERVE GIS - PHASE 2: DATA CLEANING & VALIDATION")
print("=" * 65)

hosp_report = clean_poi_dataset("hospitals.geojson", "hospitals.geojson", "Healthcare", "Hospital")
rest_report = clean_poi_dataset("restaurants.geojson", "restaurants.geojson", "Food", "Restaurant")
fuel_report = clean_poi_dataset("petrol_pumps.geojson", "petrol_pumps.geojson", "Transport", "Petrol Pump")

all_reports = [hosp_report, rest_report, fuel_report]

# Save quality report JSON
report_file = os.path.join(CLEANED_DIR, "phase2_quality_report.json")
with open(report_file, "w", encoding="utf-8") as f:
    json.dump(all_reports, f, indent=2)

# -------------------------------------------------------------
# 5. PRINT TABULAR QUALITY AUDIT REPORT
# -------------------------------------------------------------
print("\n" + "=" * 65)
print("  PHASE 2 DATA QUALITY AUDIT REPORT")
print("=" * 65)
print(f"{'Metric':<32} | {'Hospitals':<10} | {'Restaurants':<11} | {'Petrol Pumps':<12}")
print("-" * 75)
print(f"{'Total Raw POIs Collected':<32} | {hosp_report['raw_records']:<10} | {rest_report['raw_records']:<11} | {fuel_report['raw_records']:<12}")
print(f"{'Outside Study Area Removed':<32} | {hosp_report['outside_study_area_removed']:<10} | {rest_report['outside_study_area_removed']:<11} | {fuel_report['outside_study_area_removed']:<12}")
print(f"{'Duplicates Removed':<32} | {hosp_report['duplicate_records_removed']:<10} | {rest_report['duplicate_records_removed']:<11} | {fuel_report['duplicate_records_removed']:<12}")
print(f"{'Missing Names Imputed':<32} | {hosp_report['missing_names_handled']:<10} | {rest_report['missing_names_handled']:<11} | {fuel_report['missing_names_handled']:<12}")
print(f"{'Final Cleaned POIs':<32} | {hosp_report['final_valid_records']:<10} | {rest_report['final_valid_records']:<11} | {fuel_report['final_valid_records']:<12}")
print("-" * 75)
print(f"{'  -> Located in PMC':<32} | {hosp_report['pmc_records']:<10} | {rest_report['pmc_records']:<11} | {fuel_report['pmc_records']:<12}")
print(f"{'  -> Located in PCMC':<32} | {hosp_report['pcmc_records']:<10} | {rest_report['pcmc_records']:<11} | {fuel_report['pcmc_records']:<12}")
print(f"{'POIs with Phone Info':<32} | {hosp_report['records_with_phone']:<10} | {rest_report['records_with_phone']:<11} | {fuel_report['records_with_phone']:<12}")
print(f"{'POIs with Website Info':<32} | {hosp_report['records_with_website']:<10} | {rest_report['records_with_website']:<11} | {fuel_report['records_with_website']:<12}")
print("=" * 65)

# -------------------------------------------------------------
# 6. GENERATE VISUAL MAP PLOT
# -------------------------------------------------------------
gdf_clean_hosp = gpd.read_file(os.path.join(CLEANED_DIR, "hospitals.geojson"))
gdf_clean_rest = gpd.read_file(os.path.join(CLEANED_DIR, "restaurants.geojson"))
gdf_clean_fuel = gpd.read_file(os.path.join(CLEANED_DIR, "petrol_pumps.geojson"))

fig, ax = plt.subplots(figsize=(11, 9), dpi=160)

# Plot Municipal Boundaries
gdf_municipalities.plot(
    ax=ax, 
    color=["#e8f4f8", "#eafaf1"], 
    edgecolor=["#2980b9", "#27ae60"], 
    linewidth=1.6, 
    alpha=0.6
)

# Plot POIs
gdf_clean_rest.plot(ax=ax, color="#e67e22", markersize=14, alpha=0.6, label=f"Restaurants ({len(gdf_clean_rest)})")
gdf_clean_fuel.plot(ax=ax, color="#9b59b6", markersize=28, alpha=0.85, marker="^", label=f"Petrol Pumps ({len(gdf_clean_fuel)})")
gdf_clean_hosp.plot(ax=ax, color="#e74c3c", markersize=35, alpha=0.9, marker="P", label=f"Hospitals ({len(gdf_clean_hosp)})")

ax.set_title("SmartServe GIS — Phase 2 Cleaned POIs (Pune + PCMC)", fontsize=13, fontweight="bold", pad=15)
ax.set_xlabel("Longitude (EPSG:4326)", fontsize=10)
ax.set_ylabel("Latitude (EPSG:4326)", fontsize=10)
ax.grid(True, linestyle=":", alpha=0.5)
ax.legend(loc="upper left", frameon=True, facecolor="white", edgecolor="#bdc3c7", fontsize=9.5)

preview_img = os.path.join(CLEANED_DIR, "phase2_preview.png")
plt.tight_layout()
plt.savefig(preview_img)
plt.close()

print(f"\n[SUCCESS] Generated visual inspection map: {preview_img}")

# -------------------------------------------------------------
# 7. GENERATE INTERACTIVE LEAFLET INSPECTION MAP
# -------------------------------------------------------------
leaflet_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SmartServe GIS — Phase 2 POI Inspection Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    body, html {{ height: 100%; width: 100%; overflow: hidden; }}
    #map {{ height: 100%; width: 100%; }}
    .panel {{
      position: absolute; top: 16px; right: 16px; z-index: 1000;
      background: rgba(255, 255, 255, 0.96); padding: 18px; border-radius: 12px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.15); max-width: 320px;
      backdrop-filter: blur(8px); border: 1px solid rgba(0,0,0,0.08);
    }}
    .panel h2 {{ font-size: 16px; color: #1a202c; margin-bottom: 6px; }}
    .panel p {{ font-size: 12.5px; color: #4a5568; margin-bottom: 12px; line-height: 1.4; }}
    .stat-row {{ display: flex; justify-content: space-between; font-size: 13px; font-weight: 500; margin-bottom: 6px; color: #2d3748; }}
    .badge {{ padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; color: white; }}
    .badge-hosp {{ background: #e74c3c; }}
    .badge-rest {{ background: #e67e22; }}
    .badge-fuel {{ background: #9b59b6; }}
  </style>
</head>
<body>
  <div class="panel">
    <h2>🗺️ SmartServe GIS - Phase 2</h2>
    <p>Validated POIs inside PMC + PCMC study area</p>
    <div class="stat-row">
      <span>🏥 Hospitals</span>
      <span class="badge badge-hosp">{len(gdf_clean_hosp)}</span>
    </div>
    <div class="stat-row">
      <span>🍔 Restaurants</span>
      <span class="badge badge-rest">{len(gdf_clean_rest)}</span>
    </div>
    <div class="stat-row">
      <span>⛽ Petrol Pumps</span>
      <span class="badge badge-fuel">{len(gdf_clean_fuel)}</span>
    </div>
    <hr style="margin: 10px 0; border: none; border-top: 1px solid #e2e8f0;">
    <div style="font-size: 11.5px; color: #718096;">
      Total Clean POIs: <strong>{len(gdf_clean_hosp) + len(gdf_clean_rest) + len(gdf_clean_fuel)}</strong><br>
      Study Area: <strong>PMC & PCMC (427.3 km²)</strong>
    </div>
  </div>

  <div id="map"></div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    const map = L.map('map').setView([18.55, 73.85], 12);
    
    // Basemap
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }}).addTo(map);

    // Boundary Layer
    fetch('../boundary/pmc_pcmc_combined.geojson')
      .then(r => r.json())
      .then(boundaryData => {{
        L.geoJSON(boundaryData, {{
          style: feature => ({{
            color: feature.properties.municipality === 'PMC' ? '#2980b9' : '#27ae60',
            weight: 2,
            fillColor: feature.properties.municipality === 'PMC' ? '#3498db' : '#2ecc71',
            fillOpacity: 0.12
          }})
        }}).addTo(map);
      }});

    // Helper to add POI layer
    function addPoiLayer(url, color, iconSymbol, layerGroupName) {{
      const layerGroup = L.layerGroup().addTo(map);
      fetch(url)
        .then(r => r.json())
        .then(data => {{
          L.geoJSON(data, {{
            pointToLayer: (feature, latlng) => {{
              return L.circleMarker(latlng, {{
                radius: 6,
                fillColor: color,
                color: '#ffffff',
                weight: 1.5,
                opacity: 1,
                fillOpacity: 0.85
              }});
            }},
            onEachFeature: (feature, layer) => {{
              const p = feature.properties;
              layer.bindPopup(`
                <div style="font-size: 13px; line-height: 1.45;">
                  <h4 style="margin: 0 0 4px 0; color: ${{color}};">${{iconSymbol}} ${{p.name}}</h4>
                  <strong>Category:</strong> ${{p.category}} / ${{p.subcategory}}<br>
                  <strong>Municipality:</strong> ${{p.municipality}}<br>
                  <strong>Address:</strong> ${{p.address || 'N/A'}}<br>
                  ${{p.phone ? `<strong>Phone:</strong> ${{p.phone}}<br>` : ''}}
                  ${{p.website ? `<strong>Website:</strong> <a href="${{p.website}}" target="_blank">Link</a><br>` : ''}}
                  ${{p.opening_hours ? `<strong>Hours:</strong> ${{p.opening_hours}}<br>` : ''}}
                  <small style="color: #718096;">OSM ID: ${{p.osm_id}}</small>
                </div>
              `);
            }}
          }}).addTo(layerGroup);
        }});
      return layerGroup;
    }}

    const hospLayer = addPoiLayer('hospitals.geojson', '#e74c3c', '🏥', 'Hospitals');
    const fuelLayer = addPoiLayer('petrol_pumps.geojson', '#9b59b6', '⛽', 'Petrol Pumps');
    const restLayer = addPoiLayer('restaurants.geojson', '#e67e22', '🍔', 'Restaurants');

    L.control.layers(null, {{
      '🏥 Hospitals': hospLayer,
      '🍔 Restaurants': restLayer,
      '⛽ Petrol Pumps': fuelLayer
    }}, {{ collapsed: false }}).addTo(map);
  </script>
</body>
</html>
"""

html_path = os.path.join(CLEANED_DIR, "phase2_inspection_map.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(leaflet_html)

print(f"[SUCCESS] Generated interactive Leaflet POI inspection map: {html_path}\n")

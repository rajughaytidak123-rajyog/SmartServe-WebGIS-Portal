"""
SmartServe GIS - Study Area Boundary Acquisition & Validation
Script: scripts/01_fetch_and_validate_boundaries.py

Goal:
1. Download official PMC and PCMC municipal ward polygons.
2. Dissolve wards into unified municipal boundaries for PMC and PCMC.
3. Validate and enforce EPSG:4326 CRS on both layers.
4. Save separate boundaries:
   - data/boundary/pmc.geojson
   - data/boundary/pcmc.geojson
5. Merge into:
   - data/boundary/pmc_pcmc_combined.geojson (two municipal polygons with attributes)
   - data/boundary/study_area.geojson (dissolved unified spatial mask)
6. Calculate geometric & projected area metrics (sq km in UTM Zone 43N).
7. Generate visual verification preview map: data/boundary/study_area_preview.png
"""

import os
import sys
import io
import json
import requests
import geopandas as gpd
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Ensure clean UTF-8 console output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# -------------------------------------------------------------
# 1. SETUP PROJECT DIRECTORIES
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOUNDARY_DIR = os.path.join(BASE_DIR, "data", "boundary")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
CLEANED_DIR = os.path.join(BASE_DIR, "data", "cleaned")
FINAL_DIR = os.path.join(BASE_DIR, "data", "final")

for directory in [BOUNDARY_DIR, RAW_DIR, CLEANED_DIR, FINAL_DIR]:
    os.makedirs(directory, exist_ok=True)

print(f"[INFO] Initialized project directory structure under: {BASE_DIR}")

# -------------------------------------------------------------
# 2. VERIFIED MUNICIPAL BOUNDARY SOURCES
# -------------------------------------------------------------
HEADERS = {"User-Agent": "SmartServeGIS-WebGIS-Academic/1.0"}

PMC_URL = "https://cdn.jsdelivr.net/gh/datameet/Pune_wards@master/GeoData/pune-admin-wards.geojson"
PCMC_URL = "https://cdn.jsdelivr.net/gh/datameet/Pune_wards@master/GeoData/pcmc-electoral-wards.geojson"

def fetch_and_dissolve(url: str, municipality_code: str, municipality_name: str) -> gpd.GeoDataFrame:
    """
    Downloads ward-level GeoJSON, dissolves ward polygons into a single municipal
    boundary polygon, repairs any topological anomalies, and enforces EPSG:4326 CRS.
    """
    print(f"\n[INFO] Fetching boundary for {municipality_name} ({municipality_code})...")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to download data for {municipality_name} (HTTP {resp.status_code})")
        
    data = resp.json()
    gdf_wards = gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")
    print(f"       -> Successfully loaded {len(gdf_wards)} ward polygons.")
    
    # Geometric union to dissolve internal ward boundaries
    dissolved_geom = unary_union(gdf_wards.geometry)
    
    # Fix self-intersections or sliver lines if present
    if not dissolved_geom.is_valid:
        print(f"       -> [WARN] Repairing geometry topology for {municipality_code}...")
        dissolved_geom = dissolved_geom.buffer(0)
        
    gdf_boundary = gpd.GeoDataFrame(
        [{
            "municipality": municipality_code,
            "municipality_name": municipality_name,
            "num_wards": len(gdf_wards),
            "source": "Open Data / DataMeet Pune Wards",
            "crs": "EPSG:4326",
            "geometry": dissolved_geom
        }],
        crs="EPSG:4326"
    )
    return gdf_boundary

# -------------------------------------------------------------
# 3. EXECUTE BOUNDARY ACQUISITION
# -------------------------------------------------------------
print("=" * 65)
print("  SMARTSERVE GIS - PHASE 1: STUDY AREA BOUNDARY ACQUISITION")
print("=" * 65)

gdf_pmc = fetch_and_dissolve(PMC_URL, "PMC", "Pune Municipal Corporation")
gdf_pcmc = fetch_and_dissolve(PCMC_URL, "PCMC", "Pimpri-Chinchwad Municipal Corporation")

# -------------------------------------------------------------
# 4. SAVE INDIVIDUAL MUNICIPALITY GEOJSONS
# -------------------------------------------------------------
pmc_file = os.path.join(BOUNDARY_DIR, "pmc.geojson")
pcmc_file = os.path.join(BOUNDARY_DIR, "pcmc.geojson")

gdf_pmc.to_file(pmc_file, driver="GeoJSON")
gdf_pcmc.to_file(pcmc_file, driver="GeoJSON")

print(f"\n[SUCCESS] Saved PMC boundary:  {pmc_file}")
print(f"[SUCCESS] Saved PCMC boundary: {pcmc_file}")

# -------------------------------------------------------------
# 5. CREATE COMBINED AND DISSOLVED STUDY AREA
# -------------------------------------------------------------
# A. Combined boundaries (2 features: PMC and PCMC, preserving identity)
gdf_combined = gpd.GeoDataFrame(
    gpd.pd.concat([gdf_pmc, gdf_pcmc], ignore_index=True),
    crs="EPSG:4326"
)
combined_file = os.path.join(BOUNDARY_DIR, "pmc_pcmc_combined.geojson")
gdf_combined.to_file(combined_file, driver="GeoJSON")
print(f"[SUCCESS] Saved combined municipal boundaries: {combined_file}")

# B. Dissolved unified study area (1 polygon: PMC + PCMC spatial mask)
study_area_geom = unary_union([gdf_pmc.geometry.iloc[0], gdf_pcmc.geometry.iloc[0]])
if not study_area_geom.is_valid:
    study_area_geom = study_area_geom.buffer(0)

gdf_study_area = gpd.GeoDataFrame(
    [{
        "name": "Pune & Pimpri-Chinchwad Urban Agglomeration",
        "study_area": "PMC + PCMC",
        "municipalities": "PMC, PCMC",
        "crs": "EPSG:4326",
        "geometry": study_area_geom
    }],
    crs="EPSG:4326"
)
study_area_file = os.path.join(BOUNDARY_DIR, "study_area.geojson")
gdf_study_area.to_file(study_area_file, driver="GeoJSON")
print(f"[SUCCESS] Saved unified study area spatial mask: {study_area_file}")

# -------------------------------------------------------------
# 6. SPATIAL QUALITY METRICS (UTM ZONE 43N - EPSG:32643)
# -------------------------------------------------------------
pmc_area_sqkm = gdf_pmc.to_crs(epsg=32643).geometry.area.iloc[0] / 1e6
pcmc_area_sqkm = gdf_pcmc.to_crs(epsg=32643).geometry.area.iloc[0] / 1e6
study_area_sqkm = gdf_study_area.to_crs(epsg=32643).geometry.area.iloc[0] / 1e6
bounds = gdf_study_area.total_bounds

print("\n" + "=" * 65)
print("  SPATIAL VALIDATION & GEOMETRY QUALITY REPORT")
print("=" * 65)
print(f"  • PMC Validity         : {gdf_pmc.geometry.iloc[0].is_valid}")
print(f"    - Wards Count        : {gdf_pmc['num_wards'].iloc[0]}")
print(f"    - Geographic Area    : {pmc_area_sqkm:.2f} sq km")
print(f"  • PCMC Validity        : {gdf_pcmc.geometry.iloc[0].is_valid}")
print(f"    - Wards Count        : {gdf_pcmc['num_wards'].iloc[0]}")
print(f"    - Geographic Area    : {pcmc_area_sqkm:.2f} sq km")
print(f"  • Combined Study Area  : {gdf_study_area.geometry.iloc[0].is_valid}")
print(f"    - Total Area         : {study_area_sqkm:.2f} sq km")
print(f"  • Bounding Box (WGS84) : Min Lon: {bounds[0]:.4f}, Min Lat: {bounds[1]:.4f}")
print(f"                           Max Lon: {bounds[2]:.4f}, Max Lat: {bounds[3]:.4f}")
print("=" * 65)

# -------------------------------------------------------------
# 7. GENERATE VISUAL VERIFICATION PREVIEW MAP
# -------------------------------------------------------------
preview_file = os.path.join(BOUNDARY_DIR, "study_area_preview.png")

fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
gdf_pmc.plot(
    ax=ax, 
    color="#3498db", 
    edgecolor="#1a5276", 
    alpha=0.55, 
    linewidth=1.8
)
gdf_pcmc.plot(
    ax=ax, 
    color="#2ecc71", 
    edgecolor="#145a32", 
    alpha=0.55, 
    linewidth=1.8
)

patch_pmc = mpatches.Patch(facecolor="#3498db", edgecolor="#1a5276", alpha=0.55, label=f"PMC (Pune) — {pmc_area_sqkm:.1f} km²")
patch_pcmc = mpatches.Patch(facecolor="#2ecc71", edgecolor="#145a32", alpha=0.55, label=f"PCMC (Pimpri-Chinchwad) — {pcmc_area_sqkm:.1f} km²")

ax.set_title("SmartServe GIS — Study Area Boundary (PMC + PCMC)", fontsize=13, fontweight="bold", pad=15)
ax.set_xlabel("Longitude (WGS 84 / EPSG:4326)", fontsize=10)
ax.set_ylabel("Latitude (WGS 84 / EPSG:4326)", fontsize=10)
ax.grid(True, linestyle=":", alpha=0.6)
ax.legend(handles=[patch_pmc, patch_pcmc], loc="upper left", frameon=True, facecolor="white", edgecolor="#bdc3c7")

plt.tight_layout()
plt.savefig(preview_file)
plt.close()

print(f"\n[SUCCESS] Visual inspection map generated: {preview_file}\n")

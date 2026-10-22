"""
SmartServe GIS - Phase 2: Raw POI Data Collection
Script: scripts/02_fetch_raw_pois.py

Goal:
1. Query OpenStreetMap via Overpass API for 3 core service categories:
   - Hospitals    (amenity=hospital)
   - Restaurants  (amenity=restaurant)
   - Petrol Pumps (amenity=fuel)
2. Extract all nodes and center-points of ways/relations within the Pune + PCMC bounding box.
3. Save raw, unmodified GeoJSON files in data/raw/:
   - data/raw/hospitals.geojson
   - data/raw/restaurants.geojson
   - data/raw/petrol_pumps.geojson
"""

import os
import sys
import io
import time
import json
import requests
import geopandas as gpd
from shapely.geometry import Point

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# -------------------------------------------------------------
# 1. SETUP DIRECTORIES & BOUNDING BOX
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOUNDARY_FILE = os.path.join(BASE_DIR, "data", "boundary", "study_area.geojson")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# Load study area to get bounding box: [minx, miny, maxx, maxy]
gdf_study_area = gpd.read_file(BOUNDARY_FILE)
min_lon, min_lat, max_lon, max_lat = gdf_study_area.total_bounds

# Add a slight 0.01 degree buffer (~1km) for raw retrieval so we don't miss border features
bbox_str = f"{min_lat - 0.01:.4f},{min_lon - 0.01:.4f},{max_lat + 0.01:.4f},{max_lon + 0.01:.4f}"

print(f"[INFO] Initialized Raw POI Fetcher")
print(f"[INFO] Query Bounding Box (South, West, North, East): {bbox_str}")

# -------------------------------------------------------------
# 2. OVERPASS API QUERY ENGINE WITH MULTI-SERVER FALLBACK
# -------------------------------------------------------------
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]
HEADERS = {"User-Agent": "SmartServeGIS-Academic-WebGIS/1.0"}

def query_overpass(query_ql: str, retries: int = 3) -> dict:
    """Executes Overpass QL query with automatic failover across mirrors."""
    for attempt in range(retries):
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                print(f"       Querying endpoint: {endpoint.split('//')[1].split('/')[0]} (Attempt {attempt+1}/{retries})...")
                resp = requests.post(endpoint, data={"data": query_ql}, headers=HEADERS, timeout=45)
                if resp.status_code == 200:
                    data = resp.json()
                    if "elements" in data:
                        return data
                elif resp.status_code == 429:
                    print("       -> Rate limited (HTTP 429). Waiting 6 seconds...")
                    time.sleep(6)
            except Exception as e:
                print(f"       -> Connection error on {endpoint}: {e}")
                time.sleep(2)
    raise RuntimeError("Failed to query Overpass API from all available endpoints.")


def fetch_category_poi(osm_filter: str, category_name: str, subcategory_name: str, filename: str) -> str:
    """
    Queries Overpass for a specific OSM tag filter and writes raw GeoJSON.
    """
    print(f"\n[INFO] Fetching: {category_name} -> {subcategory_name} ({osm_filter})...")
    
    # Overpass QL: fetch nodes, ways, relations with center coordinates
    overpass_query = f"""
    [out:json][timeout:60];
    (
      node[{osm_filter}]({bbox_str});
      way[{osm_filter}]({bbox_str});
      relation[{osm_filter}]({bbox_str});
    );
    out body center;
    """
    
    data = query_overpass(overpass_query)
    elements = data.get("elements", [])
    print(f"       -> Received {len(elements)} raw elements from OSM.")
    
    features = []
    for el in elements:
        # Extract coordinate: if node, lat/lon; if way/relation, center.lat/center.lon
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        
        if lat is None or lon is None:
            continue
            
        tags = el.get("tags", {})
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(lon), float(lat)]
            },
            "properties": {
                "osm_id": el.get("id"),
                "osm_type": el.get("type"),
                "category_declared": category_name,
                "subcategory_declared": subcategory_name,
                "name": tags.get("name"),
                "name_en": tags.get("name:en"),
                "amenity": tags.get("amenity"),
                "healthcare": tags.get("healthcare"),
                "cuisine": tags.get("cuisine"),
                "brand": tags.get("brand"),
                "operator": tags.get("operator"),
                "addr_street": tags.get("addr:street") or tags.get("addr:full"),
                "addr_suburb": tags.get("addr:suburb") or tags.get("addr:neighbourhood") or tags.get("addr:district"),
                "addr_city": tags.get("addr:city"),
                "addr_postcode": tags.get("addr:postcode"),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "website": tags.get("website") or tags.get("contact:website"),
                "opening_hours": tags.get("opening_hours"),
                "wheelchair": tags.get("wheelchair"),
                "emergency": tags.get("emergency"),
                "all_tags": tags
            }
        }
        features.append(feature)
        
    geojson_data = {
        "type": "FeatureCollection",
        "name": f"raw_{subcategory_name.lower().replace(' ', '_')}",
        "crs": {
            "type": "name",
            "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" }
        },
        "features": features
    }
    
    out_path = os.path.join(RAW_DIR, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, ensure_ascii=False, indent=2)
        
    print(f"[SUCCESS] Saved {len(features)} features -> {out_path}")
    return out_path

# -------------------------------------------------------------
# 3. RUN EXTRACTION FOR PHASE 2 CORE SERVICES
# -------------------------------------------------------------
print("=" * 65)
print("  SMARTSERVE GIS - PHASE 2: INITIAL POI DATA EXTRACTION")
print("=" * 65)

# 1. Hospitals (Healthcare)
hosp_file = fetch_category_poi(
    osm_filter='"amenity"="hospital"',
    category_name="Healthcare",
    subcategory_name="Hospital",
    filename="hospitals.geojson"
)
time.sleep(2)  # Politeness delay between Overpass queries

# 2. Restaurants (Food)
rest_file = fetch_category_poi(
    osm_filter='"amenity"="restaurant"',
    category_name="Food",
    subcategory_name="Restaurant",
    filename="restaurants.geojson"
)
time.sleep(2)

# 3. Petrol Pumps (Transport)
fuel_file = fetch_category_poi(
    osm_filter='"amenity"="fuel"',
    category_name="Transport",
    subcategory_name="Petrol Pump",
    filename="petrol_pumps.geojson"
)

print("\n" + "=" * 65)
print("  PHASE 2 RAW POI ACQUISITION COMPLETE")
print("=" * 65)

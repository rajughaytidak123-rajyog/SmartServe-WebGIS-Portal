"""
SmartServe GIS - Phase 3: Core Multi-Service POI Data Collection
Script: scripts/04_fetch_all_core_pois.py

Goal:
1. Execute a unified Overpass QL batch query for all 20 service categories across Pune & PCMC.
2. Tag, categorize, and save separate raw GeoJSON files in data/raw/.
"""

import os
import sys
import io
import time
import json
import requests
import geopandas as gpd

# Ensure UTF-8 console encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# -------------------------------------------------------------
# 1. SETUP DIRECTORIES & BOUNDING BOX
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOUNDARY_FILE = os.path.join(BASE_DIR, "data", "boundary", "study_area.geojson")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

gdf_study_area = gpd.read_file(BOUNDARY_FILE)
min_lon, min_lat, max_lon, max_lat = gdf_study_area.total_bounds
bbox_str = f"{min_lat - 0.01:.4f},{min_lon - 0.01:.4f},{max_lat + 0.01:.4f},{max_lon + 0.01:.4f}"

print("=" * 70)
print("  SMARTSERVE GIS - PHASE 3: UNIFIED OVERPASS POI EXTRACTION")
print("=" * 70)
print(f"[INFO] Target Area Bounding Box: {bbox_str}")

# -------------------------------------------------------------
# 2. UNIFIED BATCH OVERPASS QL QUERY
# -------------------------------------------------------------
OVERPASS_QUERY = f"""
[out:json][timeout:60];
(
  // 1. Healthcare
  node["amenity"="hospital"]({bbox_str});
  way["amenity"="hospital"]({bbox_str});
  node["amenity"="clinic"]({bbox_str});
  way["amenity"="clinic"]({bbox_str});
  node["amenity"="pharmacy"]({bbox_str});
  way["amenity"="pharmacy"]({bbox_str});
  node["healthcare"="pharmacy"]({bbox_str});

  // 2. Food & Dining
  node["amenity"="restaurant"]({bbox_str});
  way["amenity"="restaurant"]({bbox_str});
  node["amenity"="cafe"]({bbox_str});
  way["amenity"="cafe"]({bbox_str});
  node["shop"="bakery"]({bbox_str});
  way["shop"="bakery"]({bbox_str});

  // 3. Transport
  node["amenity"="fuel"]({bbox_str});
  way["amenity"="fuel"]({bbox_str});
  node["amenity"="charging_station"]({bbox_str});
  way["amenity"="charging_station"]({bbox_str});
  node["railway"="station"]["station"~"subway|metro"]({bbox_str});
  node["railway"="subway_entrance"]({bbox_str});
  node["station"="subway"]({bbox_str});
  node["amenity"="bus_station"]({bbox_str});
  way["amenity"="bus_station"]({bbox_str});

  // 4. Accommodation
  node["tourism"="hotel"]({bbox_str});
  way["tourism"="hotel"]({bbox_str});

  // 5. Finance
  node["amenity"="atm"]({bbox_str});
  node["amenity"="bank"]({bbox_str});
  way["amenity"="bank"]({bbox_str});

  // 6. Emergency
  node["amenity"="police"]({bbox_str});
  way["amenity"="police"]({bbox_str});
  node["amenity"="fire_station"]({bbox_str});
  way["amenity"="fire_station"]({bbox_str});

  // 7. Education
  node["amenity"="school"]({bbox_str});
  way["amenity"="school"]({bbox_str});
  node["amenity"~"college|university"]({bbox_str});
  way["amenity"~"college|university"]({bbox_str});

  // 8. Shopping
  node["shop"="mall"]({bbox_str});
  way["shop"="mall"]({bbox_str});
  node["shop"="supermarket"]({bbox_str});
  way["shop"="supermarket"]({bbox_str});

  // 9. Recreation
  node["leisure"="park"]({bbox_str});
  way["leisure"="park"]({bbox_str});
);
out body center;
"""

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]
HEADERS = {"User-Agent": "SmartServeGIS-WebGIS-Academic/1.0"}

print("\n[INFO] Executing high-performance unified batch query on Overpass API...")
data = None
for endpoint in OVERPASS_ENDPOINTS:
    try:
        print(f"       Trying endpoint: {endpoint.split('//')[1].split('/')[0]}...")
        resp = requests.post(endpoint, data={"data": OVERPASS_QUERY}, headers=HEADERS, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            if "elements" in data and len(data["elements"]) > 0:
                print(f"       -> [SUCCESS] Downloaded {len(data['elements'])} raw features from OSM!")
                break
    except Exception as e:
        print(f"       -> Error on {endpoint}: {e}")

if not data or "elements" not in data:
    raise RuntimeError("Failed to fetch POI data from Overpass API.")

elements = data["elements"]

# -------------------------------------------------------------
# 3. CLASSIFY ELEMENTS INTO 20 CORE CATEGORIES
# -------------------------------------------------------------
category_buckets = {
    "hospitals": {"category": "Healthcare", "subcategory": "Hospital", "features": []},
    "clinics": {"category": "Healthcare", "subcategory": "Clinic", "features": []},
    "pharmacies": {"category": "Healthcare", "subcategory": "Pharmacy", "features": []},
    "restaurants": {"category": "Food", "subcategory": "Restaurant", "features": []},
    "cafes": {"category": "Food", "subcategory": "Cafe", "features": []},
    "bakeries": {"category": "Food", "subcategory": "Bakery", "features": []},
    "petrol_pumps": {"category": "Transport", "subcategory": "Petrol Pump", "features": []},
    "ev_charging": {"category": "Transport", "subcategory": "EV Charging", "features": []},
    "metro_stations": {"category": "Transport", "subcategory": "Metro Station", "features": []},
    "bus_stations": {"category": "Transport", "subcategory": "Bus Station", "features": []},
    "hotels": {"category": "Accommodation", "subcategory": "Hotel", "features": []},
    "atms": {"category": "Finance", "subcategory": "ATM", "features": []},
    "banks": {"category": "Finance", "subcategory": "Bank", "features": []},
    "police_stations": {"category": "Emergency", "subcategory": "Police Station", "features": []},
    "fire_stations": {"category": "Emergency", "subcategory": "Fire Station", "features": []},
    "schools": {"category": "Education", "subcategory": "School", "features": []},
    "colleges": {"category": "Education", "subcategory": "College", "features": []},
    "shopping_malls": {"category": "Shopping", "subcategory": "Shopping Mall", "features": []},
    "supermarkets": {"category": "Shopping", "subcategory": "Supermarket", "features": []},
    "parks": {"category": "Recreation", "subcategory": "Park", "features": []},
}

for el in elements:
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")
    if lat is None or lon is None:
        continue
        
    tags = el.get("tags", {})
    amenity = tags.get("amenity", "")
    shop = tags.get("shop", "")
    tourism = tags.get("tourism", "")
    leisure = tags.get("leisure", "")
    railway = tags.get("railway", "")
    station = tags.get("station", "")
    healthcare = tags.get("healthcare", "")

    # Match to bucket
    matched_slug = None
    if amenity == "hospital":
        matched_slug = "hospitals"
    elif amenity == "clinic":
        matched_slug = "clinics"
    elif amenity == "pharmacy" or healthcare == "pharmacy":
        matched_slug = "pharmacies"
    elif amenity == "restaurant":
        matched_slug = "restaurants"
    elif amenity == "cafe":
        matched_slug = "cafes"
    elif shop == "bakery":
        matched_slug = "bakeries"
    elif amenity == "fuel":
        matched_slug = "petrol_pumps"
    elif amenity == "charging_station":
        matched_slug = "ev_charging"
    elif railway in ["subway_entrance", "station"] and (station in ["subway", "metro"] or "subway" in railway):
        matched_slug = "metro_stations"
    elif amenity == "bus_station":
        matched_slug = "bus_stations"
    elif tourism == "hotel":
        matched_slug = "hotels"
    elif amenity == "atm":
        matched_slug = "atms"
    elif amenity == "bank":
        matched_slug = "banks"
    elif amenity == "police":
        matched_slug = "police_stations"
    elif amenity == "fire_station":
        matched_slug = "fire_stations"
    elif amenity == "school":
        matched_slug = "schools"
    elif amenity in ["college", "university"]:
        matched_slug = "colleges"
    elif shop == "mall":
        matched_slug = "shopping_malls"
    elif shop == "supermarket":
        matched_slug = "supermarkets"
    elif leisure == "park":
        matched_slug = "parks"

    if matched_slug:
        meta = category_buckets[matched_slug]
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(lon), float(lat)]
            },
            "properties": {
                "osm_id": el.get("id"),
                "osm_type": el.get("type"),
                "category_declared": meta["category"],
                "subcategory_declared": meta["subcategory"],
                "name": tags.get("name"),
                "name_en": tags.get("name:en"),
                "amenity": amenity,
                "shop": shop,
                "tourism": tourism,
                "leisure": leisure,
                "railway": railway,
                "brand": tags.get("brand"),
                "operator": tags.get("operator"),
                "cuisine": tags.get("cuisine"),
                "addr_street": tags.get("addr:street") or tags.get("addr:full"),
                "addr_suburb": tags.get("addr:suburb") or tags.get("addr:neighbourhood") or tags.get("addr:district"),
                "addr_city": tags.get("addr:city"),
                "addr_postcode": tags.get("addr:postcode"),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "website": tags.get("website") or tags.get("contact:website"),
                "opening_hours": tags.get("opening_hours"),
                "wheelchair": tags.get("wheelchair"),
                "all_tags": tags
            }
        }
        meta["features"].append(feature)

# -------------------------------------------------------------
# 4. SAVE EACH RAW CATEGORY GEOJSON
# -------------------------------------------------------------
print("\n[INFO] Saving raw GeoJSON layers into data/raw/...")
for slug, meta in category_buckets.items():
    out_path = os.path.join(RAW_DIR, f"{slug}.geojson")
    geojson_dict = {
        "type": "FeatureCollection",
        "name": f"raw_{slug}",
        "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
        "features": meta["features"]
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(geojson_dict, f, ensure_ascii=False, indent=2)
    print(f"  ✓ {meta['category']:<14} | {meta['subcategory']:<18} -> {len(meta['features']):>4} raw features -> {slug}.geojson")

print("\n" + "=" * 70)
print("  PHASE 3: ALL 20 RAW CATEGORIES EXTRACTED SUCCESSFULLY")
print("=" * 70)

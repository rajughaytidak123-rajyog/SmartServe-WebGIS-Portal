"""
SmartServe GIS - Phase 5 & 6: PostgreSQL / PostGIS Spatial Database Loader
Script: scripts/06_load_to_postgis.py

Goal:
1. Connect to PostgreSQL server using environment variables (.env).
2. Create database 'smartserve_db' if it does not exist.
3. Enable PostGIS extension and execute database/schema.sql.
4. Populate lookup tables: 'categories' and 'study_area_boundaries'.
5. Load all 4,742 POIs from data/final/all_services.geojson into 'services' table.
6. Verify spatial indexes and execute diagnostic spatial queries.
"""

import os
import sys
import io
import json
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import geopandas as gpd
from sqlalchemy import create_engine, text, URL
from dotenv import load_dotenv

# Ensure clean UTF-8 console output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# -------------------------------------------------------------
# 1. LOAD CONFIGURATION FROM .ENV
# -------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "smartserve_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASSWORD", "postgres")

print("=" * 70)
print("  SMARTSERVE GIS - PHASE 5 & 6: POSTGIS SPATIAL DATABASE LOADER")
print("=" * 70)
print(f"[CONFIG] Host: {DB_HOST}:{DB_PORT} | DB: {DB_NAME} | User: {DB_USER}")

# -------------------------------------------------------------
# 2. CREATE DATABASE IF NOT EXISTS
# -------------------------------------------------------------
def ensure_database_exists():
    """Connects to default postgres database to create target database if needed."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"[INFO] Database '{DB_NAME}' does not exist. Creating now...")
            cursor.execute(f"CREATE DATABASE {DB_NAME};")
            print(f"[SUCCESS] Database '{DB_NAME}' created successfully.")
        else:
            print(f"[INFO] Database '{DB_NAME}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Could not connect to PostgreSQL server: {e}")
        sys.exit(1)

ensure_database_exists()

# -------------------------------------------------------------
# 3. INITIALIZE SCHEMA & POSTGIS EXTENSION
# -------------------------------------------------------------
connection_url = URL.create(
    drivername="postgresql+psycopg2",
    username=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME
)
engine = create_engine(connection_url)

schema_file = os.path.join(BASE_DIR, "database", "schema.sql")
print(f"\n[INFO] Executing schema DDL from {schema_file}...")

with open(schema_file, "r", encoding="utf-8") as f:
    schema_sql = f.read()

with engine.connect() as connection:
    connection.execute(text(schema_sql))
    connection.commit()
    print("[SUCCESS] PostGIS extension enabled and spatial tables created.")

# -------------------------------------------------------------
# 4. POPULATE CATEGORIES LOOKUP TABLE
# -------------------------------------------------------------
CATEGORIES_SEED = [
    {"category": "Healthcare", "subcategory": "Hospital", "slug": "hospitals", "icon": "🏥", "color": "#e53e3e"},
    {"category": "Healthcare", "subcategory": "Clinic", "slug": "clinics", "icon": "🩺", "color": "#dd6b20"},
    {"category": "Healthcare", "subcategory": "Pharmacy", "slug": "pharmacies", "icon": "💊", "color": "#38a169"},
    {"category": "Food", "subcategory": "Restaurant", "slug": "restaurants", "icon": "🍔", "color": "#d69e2e"},
    {"category": "Food", "subcategory": "Cafe", "slug": "cafes", "icon": "☕", "color": "#805ad5"},
    {"category": "Food", "subcategory": "Bakery", "slug": "bakeries", "icon": "🥐", "color": "#b7791f"},
    {"category": "Transport", "subcategory": "Petrol Pump", "slug": "petrol_pumps", "icon": "⛽", "color": "#3182ce"},
    {"category": "Transport", "subcategory": "EV Charging", "slug": "ev_charging", "icon": "🔋", "color": "#319795"},
    {"category": "Transport", "subcategory": "Metro Station", "slug": "metro_stations", "icon": "🚇", "color": "#2b6cb0"},
    {"category": "Transport", "subcategory": "Bus Station", "slug": "bus_stations", "icon": "🚌", "color": "#4c51bf"},
    {"category": "Accommodation", "subcategory": "Hotel", "slug": "hotels", "icon": "🏨", "color": "#4a5568"},
    {"category": "Finance", "subcategory": "ATM", "slug": "atms", "icon": "🏧", "color": "#2c7a7b"},
    {"category": "Finance", "subcategory": "Bank", "slug": "banks", "icon": "🏦", "color": "#285e61"},
    {"category": "Emergency", "subcategory": "Police Station", "slug": "police_stations", "icon": "👮", "color": "#1a365d"},
    {"category": "Emergency", "subcategory": "Fire Station", "slug": "fire_stations", "icon": "🚒", "color": "#c53030"},
    {"category": "Education", "subcategory": "School", "slug": "schools", "icon": "🏫", "color": "#2f855a"},
    {"category": "Education", "subcategory": "College", "slug": "colleges", "icon": "🎓", "color": "#276749"},
    {"category": "Shopping", "subcategory": "Shopping Mall", "slug": "shopping_malls", "icon": "🛍️", "color": "#97266d"},
    {"category": "Shopping", "subcategory": "Supermarket", "slug": "supermarkets", "icon": "🛒", "color": "#702459"},
    {"category": "Recreation", "subcategory": "Park", "slug": "parks", "icon": "🌳", "color": "#22543d"}
]

print(f"\n[INFO] Populating categories lookup table ({len(CATEGORIES_SEED)} categories)...")
with engine.connect() as conn:
    for cat in CATEGORIES_SEED:
        conn.execute(text("""
            INSERT INTO categories (category, subcategory, slug, icon, color)
            VALUES (:category, :subcategory, :slug, :icon, :color)
            ON CONFLICT (subcategory) DO NOTHING;
        """), cat)
    conn.commit()
print("[SUCCESS] Categories table populated.")

# -------------------------------------------------------------
# 5. LOAD STUDY AREA BOUNDARIES (2D ENFORCED)
# -------------------------------------------------------------
combined_path = os.path.join(BASE_DIR, "data", "boundary", "pmc_pcmc_combined.geojson")
print(f"\n[INFO] Loading study area boundaries into 'study_area_boundaries'...")
gdf_comb = gpd.read_file(combined_path)

with engine.connect() as conn:
    for _, row in gdf_comb.iterrows():
        wkt_geom = row.geometry.wkt
        muni = row.get("municipality")
        muni_name = row.get("municipality_name")
        conn.execute(text("""
            INSERT INTO study_area_boundaries (name, municipality, area_sqkm, geom)
            VALUES (:name, :municipality, :area_sqkm, ST_Multi(ST_Force2D(ST_GeomFromText(:wkt, 4326))));
        """), {
            "name": muni_name,
            "municipality": muni,
            "area_sqkm": 251.0 if muni == "PMC" else 176.7,
            "wkt": wkt_geom
        })
    conn.commit()
print("[SUCCESS] Municipal boundaries loaded.")

# -------------------------------------------------------------
# 6. BATCH INSERT ALL SERVICES (4,742 POIs)
# -------------------------------------------------------------
services_path = os.path.join(BASE_DIR, "data", "final", "all_services.geojson")
print(f"\n[INFO] Reading master POI dataset from {services_path}...")
gdf_services = gpd.read_file(services_path)
total_records = len(gdf_services)

print(f"[INFO] Inserting {total_records} POIs into PostGIS 'services' table...")
conn_raw = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASS,
    dbname=DB_NAME
)
cursor = conn_raw.cursor()

insert_query = """
INSERT INTO services (
    id, name, category, subcategory, latitude, longitude,
    address, phone, website, opening_hours, operator, brand,
    wheelchair, municipality, osm_id, source, geom
) VALUES (
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)
);
"""

batch_data = []
for _, row in gdf_services.iterrows():
    batch_data.append((
        int(row["id"]),
        row["name"],
        row["category"],
        row["subcategory"],
        float(row["latitude"]),
        float(row["longitude"]),
        row.get("address"),
        row.get("phone"),
        row.get("website"),
        row.get("opening_hours"),
        row.get("operator"),
        row.get("brand"),
        row.get("wheelchair"),
        row["municipality"],
        row.get("osm_id"),
        row.get("source", "OpenStreetMap"),
        float(row["longitude"]),
        float(row["latitude"])
    ))

from psycopg2.extras import execute_batch
execute_batch(cursor, insert_query, batch_data, page_size=1000)
conn_raw.commit()
cursor.close()
conn_raw.close()

print(f"[SUCCESS] Loaded {total_records} records into PostGIS 'services' table!")

# -------------------------------------------------------------
# 7. RUN SPATIAL TEST QUERIES
# -------------------------------------------------------------
print("\n" + "=" * 70)
print("  POSTGIS SPATIAL DATABASE VERIFICATION & DIAGNOSTICS")
print("=" * 70)

with engine.connect() as conn:
    res_count = conn.execute(text("SELECT COUNT(*) FROM services;")).scalar()
    res_pmc = conn.execute(text("SELECT COUNT(*) FROM services WHERE municipality = 'PMC';")).scalar()
    res_pcmc = conn.execute(text("SELECT COUNT(*) FROM services WHERE municipality = 'PCMC';")).scalar()
    
    print(f"  • Total Services in PostGIS : {res_count}")
    print(f"    - Pune (PMC)              : {res_pmc}")
    print(f"    - PCMC                    : {res_pcmc}")
    
    # Test nearby query with Pune Station (18.5284, 73.8744)
    test_spatial = conn.execute(text("""
        SELECT 
            name, 
            subcategory, 
            ROUND(ST_Distance(geog, ST_SetSRID(ST_MakePoint(73.8744, 18.5284), 4326)::geography)::numeric, 1) AS dist_m
        FROM services
        WHERE ST_DWithin(geog, ST_SetSRID(ST_MakePoint(73.8744, 18.5284), 4326)::geography, 2000)
          AND subcategory = 'Hospital'
        ORDER BY dist_m ASC
        LIMIT 3;
    """)).fetchall()
    
    print("\n  • [SPATIAL TEST] Nearest Hospitals within 2km of Pune Station (18.5284 N, 73.8744 E):")
    for row in test_spatial:
        print(f"    -> 🏥 {row[0]} ({row[1]}) — {row[2]} meters away")

print("=" * 70)
print("\n🎉 [SUCCESS] PostGIS Database is 100% Ready for Backend Development!\n")

"""
SmartServe GIS - Major Malls & Landmark POI Enrichment
Adds prominent shopping complexes (Seasons Mall, Amanora Mall, Westend Mall, SGS Mall, Royale Heritage Mall)
to smartserve_db with exact geographic coordinates and PostGIS spatial columns.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal
from backend.app.models.service import Service
from sqlalchemy import text

MAJOR_MALLS = [
    {
        "name": "Seasons Mall",
        "category": "Shopping",
        "subcategory": "Shopping Mall",
        "latitude": 18.5196,
        "longitude": 73.9304,
        "municipality": "PMC",
        "address": "Magarpatta City, Hadapsar, Pune, 411028",
        "phone": "+91 20 6723 3000",
        "website": "https://seasonsmall.in",
        "opening_hours": "10:30-22:00",
        "operator": "Magarpatta City Development",
        "brand": "Seasons Mall",
        "wheelchair": "yes",
        "source": "Landmark Geographic Verification"
    },
    {
        "name": "Amanora Mall",
        "category": "Shopping",
        "subcategory": "Shopping Mall",
        "latitude": 18.5186,
        "longitude": 73.9348,
        "municipality": "PMC",
        "address": "Mundhwa - Kharadi Rd, Amanora Park Town, Hadapsar, Pune, 411028",
        "phone": "+91 20 6726 7888",
        "website": "https://amanoramall.com",
        "opening_hours": "11:00-22:00",
        "operator": "City Corporation Limited",
        "brand": "Amanora Mall",
        "wheelchair": "yes",
        "source": "Landmark Geographic Verification"
    },
    {
        "name": "Westend Mall",
        "category": "Shopping",
        "subcategory": "Shopping Mall",
        "latitude": 18.5606,
        "longitude": 73.8078,
        "municipality": "PMC",
        "address": "Dharmadhikari Road, Aundh, Pune, 411007",
        "phone": "+91 20 2720 7000",
        "website": "https://westendmall.in",
        "opening_hours": "11:00-22:00",
        "operator": "Westend Promoters",
        "brand": "Westend Mall",
        "wheelchair": "yes",
        "source": "Landmark Geographic Verification"
    },
    {
        "name": "SGS Mall",
        "category": "Shopping",
        "subcategory": "Shopping Mall",
        "latitude": 18.5165,
        "longitude": 73.8785,
        "municipality": "PMC",
        "address": "Moledina Road, Camp, Pune, 411001",
        "phone": "+91 20 2613 5555",
        "website": "https://sgsmall.com",
        "opening_hours": "10:00-21:30",
        "operator": "Subhash Gulati Group",
        "brand": "SGS Mall",
        "wheelchair": "yes",
        "source": "Landmark Geographic Verification"
    },
    {
        "name": "Royale Heritage Mall",
        "category": "Shopping",
        "subcategory": "Shopping Mall",
        "latitude": 18.4552,
        "longitude": 73.8967,
        "municipality": "PMC",
        "address": "NIBM Undri Road, Mohammed Wadi, Pune, 411060",
        "phone": "+91 20 6749 4000",
        "website": "https://royaleheritagemall.com",
        "opening_hours": "10:30-22:00",
        "operator": "Dorabjee Group",
        "brand": "Royale Heritage Mall",
        "wheelchair": "yes",
        "source": "Landmark Geographic Verification"
    }
]

def main():
    db = SessionLocal()
    print("=" * 60)
    print("  SMARTSERVE GIS - MAJOR MALL ENRICHMENT")
    print("=" * 60)

    # 1. Sync the primary key sequence to the max id
    db.execute(text("SELECT setval('services_id_seq', COALESCE((SELECT MAX(id) FROM services), 1));"))
    db.commit()

    inserted = 0
    for mall in MAJOR_MALLS:
        # Check if already exists
        exists = db.query(Service).filter(Service.name.ilike(f"%{mall['name']}%")).first()
        if exists:
            print(f"[EXISTS] {mall['name']} already present (ID: {exists.id})")
            continue

        # Insert record using raw SQL to populate geom cleanly (geog is generated automatically)
        sql = """
            INSERT INTO services (
                name, category, subcategory, latitude, longitude,
                municipality, address, phone, website, opening_hours,
                operator, brand, wheelchair, source, geom
            ) VALUES (
                :name, :category, :subcategory, :latitude, :longitude,
                :municipality, :address, :phone, :website, :opening_hours,
                :operator, :brand, :wheelchair, :source,
                ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)
            )
        """
        db.execute(text(sql), mall)
        inserted += 1
        print(f"[SUCCESS] Inserted: {mall['name']} at ({mall['latitude']}, {mall['longitude']})")

    db.commit()
    db.close()
    print(f"\n[DONE] Successfully enriched {inserted} major landmarks into smartserve_db!")

if __name__ == "__main__":
    main()

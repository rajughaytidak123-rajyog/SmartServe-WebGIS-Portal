"""
SmartServe GIS - Database Inspector & Summary Tool
Displays an overview of all POIs, categories, municipalities, and table structures in smartserve_db.
Uses standard ASCII formatting for universal Windows & Linux console compatibility.
"""

import sys
import os
from sqlalchemy import text

# Set UTF-8 output if possible
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import SessionLocal

def format_table(headers, rows):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))
    
    # Border strings
    sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_str = "| " + " | ".join(str(h).ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    
    lines = [sep, header_str, sep]
    for row in rows:
        row_str = "| " + " | ".join(str(val).ljust(col_widths[i]) for i, val in enumerate(row)) + " |"
        lines.append(row_str)
    lines.append(sep)
    return "\n".join(lines)

def inspect_database():
    db = SessionLocal()
    try:
        print("\n" + "=" * 78)
        print("          SMARTSERVE GIS - POSTGIS DATABASE POI SUMMARY REPORT          ")
        print("=" * 78)

        # 1. Total Count & Tables
        total_pois = db.execute(text("SELECT COUNT(*) FROM services")).scalar()
        total_boundaries = db.execute(text("SELECT COUNT(*) FROM study_area_boundaries")).scalar()
        total_categories = db.execute(text("SELECT COUNT(DISTINCT subcategory) FROM categories")).scalar()

        print(f"\n[1] CORE DATABASE METRICS")
        print(f"    - Total Points of Interest (POIs) in 'services' table : {total_pois:,}")
        print(f"    - Study Area Municipal Boundary Polygons             : {total_boundaries} (PMC & PCMC)")
        print(f"    - Standardized POI Subcategories                     : {total_categories}")

        # 2. Municipality Breakdown
        muni_rows = db.execute(text("""
            SELECT municipality, COUNT(*) as count,
                   ROUND((COUNT(*)::numeric / (SELECT COUNT(*) FROM services) * 100), 1) as pct
            FROM services
            GROUP BY municipality
            ORDER BY count DESC
        """)).fetchall()

        print(f"\n[2] MUNICIPALITY DISTRIBUTION")
        muni_data = [[r.municipality, f"{r.count:,}", f"{r.pct}%"] for r in muni_rows]
        print(format_table(["Municipality", "Total POIs", "Share (%)"], muni_data))

        # 3. Category & Subcategory Breakdown
        cat_rows = db.execute(text("""
            SELECT category, subcategory, COUNT(*) as count
            FROM services
            GROUP BY category, subcategory
            ORDER BY category, count DESC
        """)).fetchall()

        print(f"\n[3] POI BREAKDOWN BY DOMAIN & SUBCATEGORY")
        cat_data = [[r.category, r.subcategory, f"{r.count:,}"] for r in cat_rows]
        print(format_table(["Domain Category", "Subcategory", "Total POIs"], cat_data))

        # 4. Sample POIs
        sample_rows = db.execute(text("""
            SELECT id, name, category, subcategory, municipality, latitude, longitude
            FROM services
            ORDER BY id ASC
            LIMIT 10
        """)).fetchall()

        print(f"\n[4] SAMPLE POI RECORDS (First 10 of {total_pois:,})")
        sample_data = [
            [
                r.id,
                (r.name[:28] + '..') if len(r.name or '') > 28 else (r.name or 'N/A'),
                r.subcategory,
                r.municipality,
                f"{r.latitude:.4f}, {r.longitude:.4f}"
            ]
            for r in sample_rows
        ]
        print(format_table(["ID", "Facility Name", "Type", "Muni", "Coordinates"], sample_data))

        print("\n" + "=" * 78)
        print("WAYS TO EXPLORE & INSPECT ALL POIs:")
        print(" 1. Web Portal Dashboard: Open http://127.0.0.1:5500 & click 'Spatial Analytics'")
        print(" 2. Interactive Map     : Select any category in the left sidebar 'Explore' tab")
        print(" 3. Swagger REST API    : Open http://127.0.0.1:8000/docs -> /api/v1/services/search")
        print(" 4. PostgreSQL / GUI    : Query 'smartserve_db' table 'services' in pgAdmin/DBeaver")
        print(" 5. Python CLI Command  : python scripts/view_database_summary.py")
        print("=" * 78 + "\n")

    except Exception as e:
        print(f"Error inspecting database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_database()

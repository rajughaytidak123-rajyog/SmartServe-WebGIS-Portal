<div align="center">

# 🌐 SmartServe GIS — Location-Based Multi-Service WebGIS Portal

**An enterprise-grade, full-stack WebGIS platform for real-time spatial discovery, proximity buffer search, and density analytics across Pune (PMC) & Pimpri-Chinchwad (PCMC), Maharashtra, India.**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostGIS](https://img.shields.io/badge/Spatial%20DB-PostgreSQL%2016%20%2B%20PostGIS%203.6-336791.svg?logo=postgresql&logoColor=white)](https://postgis.net/)
[![Leaflet](https://img.shields.io/badge/Frontend-Leaflet%201.9.4%20%2B%20Vanilla%20ES6-199900.svg?logo=leaflet&logoColor=white)](https://leafletjs.com/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](#license)
[![OpenStreetMap](https://img.shields.io/badge/Data-OpenStreetMap%20Overpass-7EBC6F.svg?logo=openstreetmap&logoColor=white)](https://www.openstreetmap.org/)

[View Visual Showcase](#-output--visual-showcase-gallery) • [System Architecture](#-high-level-system-architecture) • [Features](#-key-features--spatial-capabilities) • [API Documentation](#-rest-api-documentation) • [Quick Start](#-quick-start-guide)

</div>

---

## 📸 Output & Visual Showcase Gallery

> **Tip for GitHub Visitors:** GitHub natively renders all `.geojson` files in this repository as interactive maps! Click on [`data/final/all_services.geojson`](data/final/all_services.geojson) or [`data/boundary/study_area.geojson`](data/boundary/study_area.geojson) to explore the spatial layers directly inside your browser without running any code!

### 1. Main WebGIS Portal & Multi-Domain Spatial Discovery
Interactive Leaflet.js map with custom 3D teardrop markers, dynamic marker clustering (4,700+ POIs), municipality filters (PMC & PCMC), and Google-style search autocomplete.

![SmartServe WebGIS Portal Overview](docs/images/01_portal_overview.png)

---

### 2. Geodesic Proximity Radius & Buffer Analysis
Real-time spatial buffering using PostGIS `ST_DWithin` on the WGS 84 ellipsoid (`GEOGRAPHY`), dynamic meter radius slider (500m – 10km), and interactive nearby facility cards sorted by ellipsoidal distance.

![Radius Buffer Proximity Analysis](docs/images/02_buffer_analysis.png)

---

### 3. Spatial Density & Distribution Analytics Dashboard
Interactive Chart.js modal rendering domain distributions, subcategory breakdowns, and municipal facility density calculations (PMC vs PCMC).

![Spatial Analytics Dashboard](docs/images/03_spatial_analytics.png)

---

### 4. High-Performance Asynchronous FastAPI Backend (Swagger UI)
Auto-generated interactive OpenAPI / Swagger UI documentation accessible at `/docs` with live endpoint testing and sub-15ms response times.

![FastAPI Swagger Documentation](docs/images/04_fastapi_swagger_docs.png)

---

### 5. Study Area Administrative Boundaries (PMC & PCMC)
Validated administrative boundaries extracted via Overpass QL with topological Point-in-Polygon (PIP) containment.

![PMC and PCMC Administrative Boundaries](docs/images/05_study_area_boundary.png)

---

## 🎯 Project Overview & Objective

Urban residents, emergency dispatchers, and city planners frequently need to identify critical services within a strict distance threshold or find the nearest essential facility in an emergency.

**SmartServe GIS** solves this with an end-to-end WebGIS architecture:
- **Study Area:** Pune Municipal Corporation (**PMC**: 331.26 km²) & Pimpri-Chinchwad Municipal Corporation (**PCMC**: 181.00 km²). Total: **512.26 km²**.
- **Dataset:** **4,747 verified Points of Interest (POIs)** across **9 domains** and **20 standardized subcategories**.
- **Dual Spatial Column Strategy:** Dual indexing using planar `GEOMETRY(Point, 4326)` for instant bounding envelope indexing and generated `GEOGRAPHY(Point, 4326)` for exact ellipsoidal geodesic meter queries (`ST_DWithin`, `ST_Distance`).

---

## 🏛️ High-Level System Architecture

```
+-----------------------------------------------------------------------------+
|                          PRESENTATION LAYER (CLIENT)                        |
|   Leaflet.js 1.9  |  Leaflet.markercluster  |  Chart.js 4.4  |  Vanilla JS   |
|   - Multi-Tile Layer Switcher (OSM / CartoDB Dark / ESRI Satellite)         |
|   - Real-Time Google-Style Search Autocomplete with Live Character Match    |
|   - 3D Teardrop Domain Markers & Radius Buffer Visualization                |
+-----------------------------------------------------------------------------+
                                      ▲
                                      │ (HTTP / JSON / RFC 7946 GeoJSON)
                                      ▼
+-----------------------------------------------------------------------------+
|                       APPLICATION LAYER (FASTAPI REST API)                  |
|   FastAPI 0.115  |  Uvicorn (ASGI)  |  Pydantic v2  |  SQLAlchemy 2.0 Core   |
|   - Geodesic Radius Filter (ST_DWithin on Geography)                        |
|   - K-Nearest Neighbors Operator (<-> R-Tree Traversal)                     |
|   - In-Database Fast GeoJSON Serialization (ST_AsGeoJSON)                   |
|   - Prefix Relevance-Ranked Type-Ahead Autocomplete Engine                  |
+-----------------------------------------------------------------------------+
                                      ▲
                                      │ (Native SQL Spatial Queries)
                                      ▼
+-----------------------------------------------------------------------------+
|                     SPATIAL DATABASE LAYER (POSTGIS 3.6)                    |
|   PostgreSQL 16  |  PostGIS 3.6 Spatial Extension  |  GIST R-Tree Indices   |
|   - Table 'services' (4,747 POIs: GEOMETRY + Generated GEOGRAPHY 4326)      |
|   - Table 'study_area_boundaries' (PMC: 331.26 km², PCMC: 181.00 km²)       |
|   - Table 'categories' (Standardized 20-Subcategory Taxonomy)               |
+-----------------------------------------------------------------------------+
```

---

## 📊 Dataset & Domain Breakdown

| Domain Category | Subcategory | Total POIs | Description & Highlights |
|:---|:---|:---:|:---|
| **Healthcare** | Hospitals | 588 | Multi-speciality, civil & private tertiary centers |
| | Clinics | 414 | Local outpatient clinics & dispensaries |
| | Pharmacies | 150 | 24x7 chemist shops & dispensaries |
| **Emergency** | Police Stations | 59 | Ward stations & police commissionerate |
| | Fire Stations | 15 | Municipal fire brigade stations |
| **Education** | Schools | 276 | Primary & secondary institutions |
| | Colleges | 168 | Engineering, medical & arts institutes |
| **Transport** | Petrol Pumps | 151 | Fuel stations with air/fuel utilities |
| | Metro Stations | 104 | Pune Metro Purple & Aqua lines |
| | Bus Stations | 79 | PMPML bus stations & transit depots |
| | EV Charging | 28 | Fast electric vehicle charging hubs |
| **Finance** | Banks | 413 | Nationalized & private commercial branches |
| | ATMs | 271 | 24/7 automated cash dispensers |
| **Food & Dining** | Restaurants | 812 | Dine-in restaurants & eateries |
| | Cafes | 298 | Cafeterias & bakeries |
| | Bakeries | 87 | Local bakeries & patisseries |
| **Shopping** | Supermarkets | 136 | Groceries, hypermarkets & marts |
| | Shopping Malls | 59 | Major commercial malls (Phoenix, Seasons, Amanora, etc.) |
| **Accommodation**| Hotels | 132 | Business hotels, lodges & guest houses |
| **Recreation** | Public Parks | 507 | Municipal parks, botanical gardens & grounds |
| **Total** | **20 Subcategories** | **4,747** | **100% Topologically Validated POIs** |

---

## 🚀 Key Features & Spatial Capabilities

1. **True Geodesic Buffer Analysis:**
   - Evaluates proximity using PostGIS `ST_DWithin(geog, ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography, :radius)`.
   - Avoids spherical distortion by computing exact meters on the WGS 84 reference ellipsoid ($R = 6371008.8\text{ m}$).

2. **K-Nearest Neighbors (KNN) Operator (`<->`):**
   - Retrieves the closest $K$ facilities via direct R-Tree bounding-box index traversal.
   - Executes in **sub-2ms**, critical for emergency response (finding nearest hospital or police station).

3. **In-Database GeoJSON Serialization:**
   - Queries generate RFC 7946 GeoJSON directly inside PostgreSQL via `ST_AsGeoJSON(geom)` and `json_build_object`.
   - Eliminates Python object serialization overhead for high throughput.

4. **Real-Time Google-Style Autocomplete:**
   - Features prefix-matched type-ahead search with highlighted matching characters and keyboard navigation (`↑`, `↓`, `↵`, `Esc`).

5. **Multi-Basemap Switcher & Boundary Overlay:**
   - Seamless toggling between OpenStreetMap Standard, CartoDB Dark Matter, and ESRI World Imagery Satellite tiles.
   - Interactive municipal boundary polygon fills for PMC and PCMC.

---

## 📡 REST API Documentation

The backend exposes RESTful endpoints with interactive Swagger UI docs at `http://127.0.0.1:8000/docs`:

### Core Endpoints

| Method | Endpoint | Description | Query Parameters |
|:---|:---|:---|:---|
| `GET` | `/health` | System health, database connection & latency | None |
| `GET` | `/api/v1/services/nearby` | Proximity search within radius meters | `lat`, `lon`, `radius`, `category`, `municipality`, `limit` |
| `GET` | `/api/v1/services/knn` | K-Nearest Neighbors search | `lat`, `lon`, `k`, `subcategory` |
| `GET` | `/api/v1/services/autocomplete`| Type-ahead search suggestions | `q`, `limit` |
| `GET` | `/api/v1/services/geojson` | In-database GeoJSON streaming | `category`, `subcategory`, `municipality` |
| `GET` | `/api/v1/boundaries` | PMC & PCMC administrative GeoJSON | None |
| `GET` | `/api/v1/analytics/density` | Spatial density per km² by municipality | None |
| `GET` | `/api/v1/categories/tree` | Hierarchical category taxonomy | None |

#### Example: Proximity Search
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/services/nearby?lat=18.5204&lon=73.8567&radius=2000&subcategory=Hospital"
```

#### Example Response (GeoJSON FeatureCollection):
```json
{
  "type": "FeatureCollection",
  "count": 14,
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [73.8696, 18.5251]
      },
      "properties": {
        "id": 1,
        "name": "Sassoon General Hospital",
        "category": "Healthcare",
        "subcategory": "Hospital",
        "municipality": "PMC",
        "distance_meters": 1482.35,
        "address": "Near Pune Railway Station, Pune"
      }
    }
  ]
}
```

---

## 🛠️ Tech Stack & Dependencies

- **Database:** PostgreSQL 16 + PostGIS 3.6 Spatial Extension
- **Backend:** Python 3.14, FastAPI 0.115, Uvicorn (ASGI), SQLAlchemy 2.0 Core, Pydantic v2
- **Frontend:** Leaflet.js 1.9.4, Leaflet.markercluster 1.5.3, Chart.js 4.4, FontAwesome 6, Vanilla CSS3 / HTML5 / Modern ES6 JS
- **Data Engineering:** GeoPandas, Shapely 2.0, Requests, Overpass QL

---

## 💻 Quick Start Guide

### Prerequisites
1. **Python 3.10+** (Tested on Python 3.14)
2. **PostgreSQL 16** with **PostGIS 3.x** installed
3. A running PostgreSQL instance on port `5432`

### 1. Clone the Repository
```bash
git clone https://github.com/rajughaytidak123-rajyog/SmartServe-WebGIS-Portal.git
cd SmartServe-WebGIS-Portal
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your PostgreSQL credentials:
```bash
cp .env.example .env
```
Example `.env`:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smartserve_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=smartserve_db
PORT=8000
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize Database & Ingest Data
```bash
python scripts/06_load_to_postgis.py
```
To verify the database summary at any time:
```bash
python scripts/view_database_summary.py
```

### 5. Launch the Application
You can use the one-click batch launcher:
```cmd
run_all.bat
```
Or start the backend and frontend separately in two terminals:

**Terminal 1 (Backend):**
```bash
python backend/run.py
# Server runs at http://127.0.0.1:8000
# Swagger UI at http://127.0.0.1:8000/docs
```

**Terminal 2 (Frontend):**
```bash
python frontend/serve.py
# Web Portal runs at http://127.0.0.1:5500
```

---

## 📂 Project Directory Structure

```
SmartServe-WebGIS-Portal/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/  # FastAPI route handlers (services, boundaries, analytics)
│   │   ├── core/              # Settings & database configuration
│   │   ├── db/                # SQLAlchemy session & base engine
│   │   ├── models/            # Relational models
│   │   └── schemas/           # Pydantic v2 validation models
│   └── run.py                 # Backend launcher with Uvicorn
├── data/
│   ├── boundary/              # PMC & PCMC boundary GeoJSONs & previews
│   ├── cleaned/               # Standardized POIs (20 subcategories) & inspection map
│   ├── final/                 # Unified all_services.geojson (4,747 features)
│   └── raw/                   # Raw Overpass QL extraction files
├── database/
│   ├── schema.sql             # SQL DDL table schema with GIST indices
│   └── spatial_queries.sql    # Benchmark SQL spatial queries
├── docs/
│   └── images/                # High-res screenshots for README showcase
├── frontend/
│   ├── css/                   # Leaflet custom styles & modern dashboard styling
│   ├── js/                    # Modular ES6 controllers (map.js, api.js, charts.js, app.js)
│   ├── index.html             # Main WebGIS interactive single-page application
│   └── serve.py               # Lightweight frontend HTTP server
├── scripts/                   # Data ETL pipelines (fetch, clean, deduplicate, load)
├── requirements.txt           # Python library dependencies
├── run_all.bat                # Windows one-click launcher
└── PROJECT_DOCUMENTATION_AND_VIVA_GUIDE.md # Detailed 280+ line academic & viva guide
```

---

## 🎓 Academic Documentation & Viva Voce Guide

A comprehensive viva voce guide covering spatial indexing, coordinate reference systems (`EPSG:4326` vs planar projections), great-circle trigonometry, and database optimization is available in:
- Markdown: [`PROJECT_DOCUMENTATION_AND_VIVA_GUIDE.md`](PROJECT_DOCUMENTATION_AND_VIVA_GUIDE.md)
- PDF: [`SmartServe_GIS_Complete_Project_Documentation_and_Viva_Guide.pdf`](SmartServe_GIS_Complete_Project_Documentation_and_Viva_Guide.pdf)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
Data source © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL).

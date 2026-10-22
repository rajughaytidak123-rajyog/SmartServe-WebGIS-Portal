-- ============================================================================
-- SmartServe GIS - Database Schema & PostGIS Configuration
-- Database: smartserve_db
-- ============================================================================

-- 1. ENABLE POSTGIS SPATIAL EXTENSION
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. DROP EXISTING TABLES FOR CLEAN INITIALIZATION
DROP TABLE IF EXISTS services CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS study_area_boundaries CASCADE;

-- 3. CREATE CATEGORIES LOOKUP TABLE
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    category VARCHAR(64) NOT NULL,
    subcategory VARCHAR(64) NOT NULL UNIQUE,
    slug VARCHAR(64) NOT NULL UNIQUE,
    icon VARCHAR(10) NOT NULL,
    color VARCHAR(20) NOT NULL DEFAULT '#3182ce',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. CREATE STUDY AREA BOUNDARIES TABLE
CREATE TABLE study_area_boundaries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    municipality VARCHAR(20),
    area_sqkm DOUBLE PRECISION,
    source VARCHAR(100) DEFAULT 'DataMeet / OpenStreetMap',
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);

-- 5. CREATE CORE SERVICES SPATIAL TABLE
CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    subcategory VARCHAR(64) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    address TEXT,
    phone VARCHAR(100),
    website VARCHAR(255),
    opening_hours VARCHAR(255),
    operator VARCHAR(150),
    brand VARCHAR(150),
    wheelchair VARCHAR(50),
    municipality VARCHAR(10) NOT NULL CHECK (municipality IN ('PMC', 'PCMC')),
    osm_id VARCHAR(50),
    source VARCHAR(50) DEFAULT 'OpenStreetMap',
    
    -- PostGIS Geometry (Planar / WGS 84 display)
    geom GEOMETRY(Point, 4326) NOT NULL,
    
    -- PostGIS Geography (Spherical metric geodesic calculation stored column)
    geog GEOGRAPHY(Point, 4326) GENERATED ALWAYS AS (geom::geography) STORED,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. CREATE HIGH-PERFORMANCE SPATIAL & ATTRIBUTE INDEXES
-- A. GIST R-Tree Spatial Index on Geometry
CREATE INDEX idx_services_geom ON services USING GIST (geom);

-- B. GIST Spatial Index on Geography (optimizes ST_DWithin and ST_Distance in meters)
CREATE INDEX idx_services_geog ON services USING GIST (geog);

-- C. GIST Spatial Index on Boundaries
CREATE INDEX idx_boundaries_geom ON study_area_boundaries USING GIST (geom);

-- D. B-Tree Indexes on filtering attributes
CREATE INDEX idx_services_category ON services (category);
CREATE INDEX idx_services_subcategory ON services (subcategory);
CREATE INDEX idx_services_municipality ON services (municipality);
CREATE INDEX idx_services_name ON services (name);

-- E. Composite Index for category + municipality filtering
CREATE INDEX idx_services_cat_muni ON services (category, municipality);

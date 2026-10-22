-- ============================================================================
-- SmartServe GIS - Standard PostGIS Spatial Queries Reference
-- These queries power the FastAPI backend and spatial analytics.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- QUERY 1: NEARBY / RADIUS SEARCH (ST_DWithin in meters)
-- Find all Hospitals within 3 km (3000m) of Pune Railway Station (18.5284, 73.8744)
-- ----------------------------------------------------------------------------
SELECT 
    id,
    name,
    subcategory,
    municipality,
    address,
    phone,
    -- Calculate spherical geodesic distance in meters and round to nearest meter
    ROUND(ST_Distance(geog, ST_SetSRID(ST_MakePoint(73.8744, 18.5284), 4326)::geography)::numeric, 1) AS distance_meters,
    latitude,
    longitude
FROM services
WHERE 
    subcategory = 'Hospital'
    AND ST_DWithin(
        geog, 
        ST_SetSRID(ST_MakePoint(73.8744, 18.5284), 4326)::geography, 
        3000
    )
ORDER BY distance_meters ASC;


-- ----------------------------------------------------------------------------
-- QUERY 2: K-NEAREST NEIGHBOR (KNN) FAST SEARCH (<-> Spatial Operator)
-- Find the 5 closest Petrol Pumps to a user location using index-accelerated KNN
-- ----------------------------------------------------------------------------
SELECT 
    id,
    name,
    subcategory,
    municipality,
    address,
    ROUND(ST_Distance(geog, ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326)::geography)::numeric, 1) AS distance_meters,
    latitude,
    longitude
FROM services
WHERE subcategory = 'Petrol Pump'
ORDER BY geom <-> ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326)
LIMIT 5;


-- ----------------------------------------------------------------------------
-- QUERY 3: MULTI-CATEGORY "EXPLORE NEARBY" SUMMARY
-- Count all nearby services grouped by subcategory within 2 km of user
-- ----------------------------------------------------------------------------
SELECT 
    category,
    subcategory,
    COUNT(*) AS total_nearby,
    MIN(ROUND(ST_Distance(geog, ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326)::geography)::numeric, 0)) AS nearest_distance_meters
FROM services
WHERE ST_DWithin(
    geog, 
    ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326)::geography, 
    2000
)
GROUP BY category, subcategory
ORDER BY total_nearby DESC;


-- ----------------------------------------------------------------------------
-- QUERY 4: SPATIAL POINT-IN-POLYGON AGGREGATION
-- Count POIs per municipality using spatial intersection with boundary polygons
-- ----------------------------------------------------------------------------
SELECT 
    b.name AS boundary_name,
    b.municipality,
    COUNT(s.id) AS service_count,
    ROUND((COUNT(s.id)::numeric / b.area_sqkm)::numeric, 2) AS service_density_per_sqkm
FROM study_area_boundaries b
LEFT JOIN services s ON ST_Within(s.geom, b.geom)
WHERE b.municipality IS NOT NULL
GROUP BY b.id, b.name, b.municipality, b.area_sqkm
ORDER BY service_count DESC;


-- ----------------------------------------------------------------------------
-- QUERY 5: GEOJSON FEATURECOLLECTION EXPORT DIRECTLY FROM POSTGIS
-- Generate full GeoJSON output natively in SQL using ST_AsGeoJSON
-- ----------------------------------------------------------------------------
SELECT json_build_object(
    'type', 'FeatureCollection',
    'features', json_agg(
        json_build_object(
            'type', 'Feature',
            'geometry', ST_AsGeoJSON(geom)::json,
            'properties', json_build_object(
                'id', id,
                'name', name,
                'category', category,
                'subcategory', subcategory,
                'municipality', municipality,
                'address', address,
                'phone', phone,
                'website', website,
                'opening_hours', opening_hours
            )
        )
    )
) AS geojson_output
FROM services
WHERE category = 'Emergency';

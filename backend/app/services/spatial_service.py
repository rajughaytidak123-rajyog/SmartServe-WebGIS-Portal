import json
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.schemas.service import NearbyServiceResponse, ServiceResponse
from backend.app.schemas.stats import (
    DensityStat,
    DensityResponse,
    NearbyCategorySummaryItem,
    NearbyCategorySummaryResponse,
    MunicipalityStat,
    CategoryStat,
    SubcategoryStat,
    OverviewStats
)

class SpatialService:
    @staticmethod
    def _build_keyword_clauses(q: str, params: Dict[str, Any], prefix: str = "kw") -> List[str]:
        clauses = []
        tokens = [t.strip() for t in q.strip().split() if t.strip()]
        for idx, token in enumerate(tokens):
            pname = f"{prefix}_{idx}"
            base_token = token.rstrip('s') if len(token) > 4 and token.endswith('s') else token
            clauses.append(
                f"(name ILIKE :{pname} OR address ILIKE :{pname} OR brand ILIKE :{pname} OR subcategory ILIKE :{pname} OR category ILIKE :{pname})"
            )
            params[pname] = f"%{base_token}%"
        return clauses

    @staticmethod
    def get_nearby_services(
        db: Session,
        lat: float,
        lon: float,
        radius_meters: float = 2000.0,
        q: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        municipality: Optional[str] = None,
        limit: int = 200,
        offset: int = 0
    ) -> Tuple[List[NearbyServiceResponse], int]:
        """
        Query POIs within a given radius (in meters) of a user location using PostGIS ST_DWithin on geography.
        Returns list of services with exact geodesic distance (in meters and km) and estimated travel times.
        """
        where_clauses = [
            "ST_DWithin(geog, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius)"
        ]
        params: Dict[str, Any] = {
            "lat": lat,
            "lon": lon,
            "radius": radius_meters,
            "limit": limit,
            "offset": offset
        }

        if q and q.strip():
            where_clauses.extend(SpatialService._build_keyword_clauses(q, params, "near_kw"))

        if category:
            where_clauses.append("category ILIKE :category")
            params["category"] = category

        if subcategory:
            where_clauses.append("subcategory ILIKE :subcategory")
            params["subcategory"] = subcategory

        if municipality:
            where_clauses.append("municipality ILIKE :municipality")
            params["municipality"] = municipality

        where_sql = " AND ".join(where_clauses)

        # Count total matching query
        count_sql = f"SELECT COUNT(*) FROM services WHERE {where_sql}"
        total_count = db.execute(text(count_sql), params).scalar() or 0

        # Query services sorted by distance
        query_sql = f"""
            SELECT 
                id,
                name,
                category,
                subcategory,
                latitude,
                longitude,
                municipality,
                address,
                phone,
                website,
                opening_hours,
                operator,
                brand,
                wheelchair,
                osm_id,
                source,
                created_at,
                ROUND(ST_Distance(geog, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)::numeric, 1) AS distance_meters
            FROM services
            WHERE {where_sql}
            ORDER BY distance_meters ASC
            LIMIT :limit OFFSET :offset
        """
        rows = db.execute(text(query_sql), params).fetchall()

        results = []
        for r in rows:
            dist_m = float(r.distance_meters)
            dist_km = round(dist_m / 1000.0, 2)
            # Estimate walk time (at ~4.8 km/h => 80 meters/min)
            walk_min = round(dist_m / 80.0, 1)
            # Estimate drive time (at ~24 km/h => 400 meters/min in urban traffic)
            drive_min = round(max(dist_m / 400.0, 1.0), 1)

            results.append(
                NearbyServiceResponse(
                    id=r.id,
                    name=r.name,
                    category=r.category,
                    subcategory=r.subcategory,
                    latitude=r.latitude,
                    longitude=r.longitude,
                    municipality=r.municipality,
                    address=r.address,
                    phone=r.phone,
                    website=r.website,
                    opening_hours=r.opening_hours,
                    operator=r.operator,
                    brand=r.brand,
                    wheelchair=r.wheelchair,
                    osm_id=r.osm_id,
                    source=r.source,
                    created_at=r.created_at,
                    distance_meters=dist_m,
                    distance_km=dist_km,
                    walk_time_min=walk_min,
                    drive_time_min=drive_min
                )
            )

        return results, total_count

    @staticmethod
    def get_knn_services(
        db: Session,
        lat: float,
        lon: float,
        k: int = 5,
        q: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        municipality: Optional[str] = None
    ) -> List[NearbyServiceResponse]:
        """
        K-Nearest Neighbor query using PostGIS spatial operator `<->` for index-accelerated instant lookup.
        """
        where_clauses = []
        params: Dict[str, Any] = {
            "lat": lat,
            "lon": lon,
            "k": k
        }

        if q and q.strip():
            where_clauses.extend(SpatialService._build_keyword_clauses(q, params, "knn_kw"))

        if category:
            where_clauses.append("category ILIKE :category")
            params["category"] = category

        if subcategory:
            where_clauses.append("subcategory ILIKE :subcategory")
            params["subcategory"] = subcategory

        if municipality:
            where_clauses.append("municipality ILIKE :municipality")
            params["municipality"] = municipality

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query_sql = f"""
            SELECT 
                id,
                name,
                category,
                subcategory,
                latitude,
                longitude,
                municipality,
                address,
                phone,
                website,
                opening_hours,
                operator,
                brand,
                wheelchair,
                osm_id,
                source,
                created_at,
                ROUND(ST_Distance(geog, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)::numeric, 1) AS distance_meters
            FROM services
            {where_sql}
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            LIMIT :k
        """
        rows = db.execute(text(query_sql), params).fetchall()

        results = []
        for r in rows:
            dist_m = float(r.distance_meters)
            dist_km = round(dist_m / 1000.0, 2)
            walk_min = round(dist_m / 80.0, 1)
            drive_min = round(max(dist_m / 400.0, 1.0), 1)

            results.append(
                NearbyServiceResponse(
                    id=r.id,
                    name=r.name,
                    category=r.category,
                    subcategory=r.subcategory,
                    latitude=r.latitude,
                    longitude=r.longitude,
                    municipality=r.municipality,
                    address=r.address,
                    phone=r.phone,
                    website=r.website,
                    opening_hours=r.opening_hours,
                    operator=r.operator,
                    brand=r.brand,
                    wheelchair=r.wheelchair,
                    osm_id=r.osm_id,
                    source=r.source,
                    created_at=r.created_at,
                    distance_meters=dist_m,
                    distance_km=dist_km,
                    walk_time_min=walk_min,
                    drive_time_min=drive_min
                )
            )

        return results

    @staticmethod
    def search_services(
        db: Session,
        q: Optional[str] = None,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        municipality: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[ServiceResponse], int]:
        """
        Search and filter services by name, address, category, subcategory, municipality.
        """
        where_clauses = []
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset
        }

        if q and q.strip():
            where_clauses.extend(SpatialService._build_keyword_clauses(q, params, "search_kw"))

        if category:
            where_clauses.append("category ILIKE :category")
            params["category"] = category

        if subcategory:
            where_clauses.append("subcategory ILIKE :subcategory")
            params["subcategory"] = subcategory

        if municipality:
            where_clauses.append("municipality ILIKE :municipality")
            params["municipality"] = municipality

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        count_sql = f"SELECT COUNT(*) FROM services {where_sql}"
        total_count = db.execute(text(count_sql), params).scalar() or 0

        query_sql = f"""
            SELECT 
                id, name, category, subcategory, latitude, longitude,
                municipality, address, phone, website, opening_hours,
                operator, brand, wheelchair, osm_id, source, created_at
            FROM services
            {where_sql}
            ORDER BY name ASC
            LIMIT :limit OFFSET :offset
        """
        rows = db.execute(text(query_sql), params).fetchall()

        items = [
            ServiceResponse(
                id=r.id,
                name=r.name,
                category=r.category,
                subcategory=r.subcategory,
                latitude=r.latitude,
                longitude=r.longitude,
                municipality=r.municipality,
                address=r.address,
                phone=r.phone,
                website=r.website,
                opening_hours=r.opening_hours,
                operator=r.operator,
                brand=r.brand,
                wheelchair=r.wheelchair,
                osm_id=r.osm_id,
                source=r.source,
                created_at=r.created_at
            )
            for r in rows
        ]

        return items, total_count

    @staticmethod
    def get_services_geojson(
        db: Session,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        municipality: Optional[str] = None,
        bbox: Optional[str] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Generate high-speed GeoJSON FeatureCollection natively inside PostgreSQL using ST_AsGeoJSON.
        Supports Bounding Box filtering (min_lon, min_lat, max_lon, max_lat).
        """
        where_clauses = []
        params: Dict[str, Any] = {"limit": limit}

        if category:
            where_clauses.append("category ILIKE :category")
            params["category"] = category

        if subcategory:
            where_clauses.append("subcategory ILIKE :subcategory")
            params["subcategory"] = subcategory

        if municipality:
            where_clauses.append("municipality ILIKE :municipality")
            params["municipality"] = municipality

        if bbox:
            try:
                coords = [float(x.strip()) for x in bbox.split(",")]
                if len(coords) == 4:
                    min_lon, min_lat, max_lon, max_lat = coords
                    where_clauses.append("geom && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)")
                    params["min_lon"] = min_lon
                    params["min_lat"] = min_lat
                    params["max_lon"] = max_lon
                    params["max_lat"] = max_lat
            except Exception:
                pass

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query_sql = f"""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(
                    json_agg(
                        json_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(geom)::json,
                            'properties', json_build_object(
                                'id', id,
                                'name', name,
                                'category', category,
                                'subcategory', subcategory,
                                'latitude', latitude,
                                'longitude', longitude,
                                'municipality', municipality,
                                'address', address,
                                'phone', phone,
                                'website', website,
                                'opening_hours', opening_hours,
                                'operator', operator,
                                'brand', brand,
                                'wheelchair', wheelchair
                            )
                        )
                    ),
                    '[]'::json
                )
            ) AS geojson
            FROM (
                SELECT * FROM services
                {where_sql}
                LIMIT :limit
            ) sub;
        """
        row = db.execute(text(query_sql), params).fetchone()
        if row and row.geojson:
            if isinstance(row.geojson, str):
                return json.loads(row.geojson)
            return row.geojson
        return {"type": "FeatureCollection", "features": []}

    @staticmethod
    def get_boundaries_geojson(db: Session, municipality: Optional[str] = None) -> Dict[str, Any]:
        """
        Export municipal boundary polygons (PMC & PCMC) as native GeoJSON FeatureCollection.
        """
        where_clauses = []
        params: Dict[str, Any] = {}

        if municipality:
            where_clauses.append("municipality = :municipality")
            params["municipality"] = municipality

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query_sql = f"""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(
                    json_agg(
                        json_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(geom)::json,
                            'properties', json_build_object(
                                'id', id,
                                'name', name,
                                'municipality', municipality,
                                'area_sqkm', area_sqkm,
                                'source', source
                            )
                        )
                    ),
                    '[]'::json
                )
            ) AS geojson
            FROM study_area_boundaries
            {where_sql};
        """
        row = db.execute(text(query_sql), params).fetchone()
        if row and row.geojson:
            if isinstance(row.geojson, str):
                return json.loads(row.geojson)
            return row.geojson
        return {"type": "FeatureCollection", "features": []}

    @staticmethod
    def get_density_analysis(db: Session) -> DensityResponse:
        """
        Perform spatial point-in-polygon aggregation to compute POI count and density per sq.km.
        """
        query_sql = """
            SELECT 
                b.name AS boundary_name,
                b.municipality,
                b.area_sqkm,
                COUNT(s.id) AS total_pois,
                ROUND((COUNT(s.id)::numeric / NULLIF(b.area_sqkm, 0))::numeric, 2) AS density_per_sqkm
            FROM study_area_boundaries b
            LEFT JOIN services s ON ST_Within(s.geom, b.geom)
            WHERE b.municipality IS NOT NULL
            GROUP BY b.id, b.name, b.municipality, b.area_sqkm
            ORDER BY total_pois DESC;
        """
        rows = db.execute(text(query_sql)).fetchall()

        total_area = 0.0
        total_pois = 0
        stat_items = []

        for r in rows:
            area = float(r.area_sqkm or 0.0)
            pois = int(r.total_pois)
            density = float(r.density_per_sqkm or 0.0)
            total_area += area
            total_pois += pois

            stat_items.append(
                DensityStat(
                    boundary_name=r.boundary_name,
                    municipality=r.municipality or "Unknown",
                    area_sqkm=round(area, 2),
                    total_pois=pois,
                    density_per_sqkm=density
                )
            )

        overall_density = round(total_pois / total_area, 2) if total_area > 0 else 0.0

        return DensityResponse(
            study_area="Pune Metropolitan Area (PMC & PCMC)",
            total_area_sqkm=round(total_area, 2),
            overall_density_per_sqkm=overall_density,
            boundaries=stat_items
        )

    @staticmethod
    def get_nearby_summary(
        db: Session,
        lat: float,
        lon: float,
        radius_meters: float = 2000.0
    ) -> NearbyCategorySummaryResponse:
        """
        Count nearby services grouped by subcategory within radius of a point.
        """
        query_sql = """
            SELECT 
                category,
                subcategory,
                COUNT(*) AS total_nearby,
                MIN(ROUND(ST_Distance(geog, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography)::numeric, 1)) AS nearest_distance_meters
            FROM services
            WHERE ST_DWithin(
                geog, 
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, 
                :radius
            )
            GROUP BY category, subcategory
            ORDER BY total_nearby DESC;
        """
        rows = db.execute(text(query_sql), {"lat": lat, "lon": lon, "radius": radius_meters}).fetchall()

        breakdown = []
        total_count = 0
        for r in rows:
            cnt = int(r.total_nearby)
            total_count += cnt
            breakdown.append(
                NearbyCategorySummaryItem(
                    category=r.category,
                    subcategory=r.subcategory,
                    total_nearby=cnt,
                    nearest_distance_meters=float(r.nearest_distance_meters)
                )
            )

        return NearbyCategorySummaryResponse(
            center_latitude=lat,
            center_longitude=lon,
            radius_meters=radius_meters,
            total_services_nearby=total_count,
            breakdown=breakdown
        )

    @staticmethod
    def get_overview_statistics(db: Session) -> OverviewStats:
        """
        Generate global overview statistics.
        """
        total_services = db.execute(text("SELECT COUNT(*) FROM services")).scalar() or 0
        total_categories = db.execute(text("SELECT COUNT(DISTINCT category) FROM categories")).scalar() or 0
        total_subcategories = db.execute(text("SELECT COUNT(DISTINCT subcategory) FROM categories")).scalar() or 0

        # Municipality breakdown
        muni_rows = db.execute(text("""
            SELECT municipality, COUNT(*) AS count
            FROM services
            GROUP BY municipality
            ORDER BY count DESC
        """)).fetchall()

        municipalities = [
            MunicipalityStat(
                municipality=r.municipality,
                count=r.count,
                percentage=round((r.count / total_services * 100.0), 1) if total_services > 0 else 0.0
            )
            for r in muni_rows
        ]

        # Top categories with icons
        cat_rows = db.execute(text("""
            SELECT s.category, COUNT(s.id) AS count, c.icon, c.color
            FROM services s
            LEFT JOIN (
                SELECT DISTINCT ON (category) category, icon, color 
                FROM categories
            ) c ON s.category = c.category
            GROUP BY s.category, c.icon, c.color
            ORDER BY count DESC
        """)).fetchall()

        top_categories = [
            CategoryStat(
                category=r.category,
                count=r.count,
                percentage=round((r.count / total_services * 100.0), 1) if total_services > 0 else 0.0,
                icon=r.icon or "📍",
                color=r.color or "#3182ce"
            )
            for r in cat_rows
        ]

        # Top subcategories
        subcat_rows = db.execute(text("""
            SELECT s.category, s.subcategory, COUNT(s.id) AS count, c.icon
            FROM services s
            LEFT JOIN categories c ON s.subcategory = c.subcategory
            GROUP BY s.category, s.subcategory, c.icon
            ORDER BY count DESC
            LIMIT 10
        """)).fetchall()

        top_subcategories = [
            SubcategoryStat(
                category=r.category,
                subcategory=r.subcategory,
                count=r.count,
                icon=r.icon or "📍"
            )
            for r in subcat_rows
        ]

        return OverviewStats(
            total_services=total_services,
            total_categories=total_categories,
            total_subcategories=total_subcategories,
            municipalities=municipalities,
            top_categories=top_categories,
            top_subcategories=top_subcategories
        )

    @staticmethod
    def get_autocomplete_suggestions(
        db: Session,
        q: str,
        limit: int = 8
    ) -> List[Dict[str, Any]]:
        """
        Fast real-time autocomplete suggestions with relevance ranking (prefix match > substring match).
        """
        if not q or not q.strip():
            return []

        clean_q = q.strip()
        base_token = clean_q.rstrip('s') if len(clean_q) > 4 and clean_q.endswith('s') else clean_q

        sql = """
            SELECT 
                id, name, category, subcategory, latitude, longitude,
                municipality, address,
                CASE 
                    WHEN name ILIKE :prefix THEN 1
                    WHEN name ILIKE :contains THEN 2
                    WHEN subcategory ILIKE :prefix THEN 3
                    WHEN subcategory ILIKE :contains THEN 4
                    ELSE 5
                END AS match_rank
            FROM services
            WHERE name ILIKE :contains 
               OR subcategory ILIKE :contains 
               OR category ILIKE :contains
               OR address ILIKE :contains
            ORDER BY match_rank ASC, name ASC
            LIMIT :limit
        """
        rows = db.execute(text(sql), {
            "prefix": f"{clean_q}%",
            "contains": f"%{base_token}%",
            "limit": limit
        }).fetchall()

        return [
            {
                "id": r.id,
                "name": r.name,
                "category": r.category,
                "subcategory": r.subcategory,
                "latitude": float(r.latitude) if r.latitude is not None else None,
                "longitude": float(r.longitude) if r.longitude is not None else None,
                "municipality": r.municipality,
                "address": r.address
            }
            for r in rows
        ]

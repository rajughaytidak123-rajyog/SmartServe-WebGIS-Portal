import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def run_tests():
    print("=" * 75)
    print("  SMARTSERVE GIS - BACKEND API AUTOMATED TEST SUITE")
    print("=" * 75)

    tests_passed = 0
    total_tests = 0

    def assert_test(name, condition, detail=""):
        nonlocal tests_passed, total_tests
        total_tests += 1
        if condition:
            print(f"  [PASS] {name} {detail}")
            tests_passed += 1
        else:
            print(f"  [FAIL] {name} {detail}")

    # TEST 1: Root endpoint
    res = client.get("/")
    assert_test("GET / (Root API Metadata)", res.status_code == 200 and res.json().get("status") == "online")

    # TEST 2: Health check
    res = client.get("/health")
    data = res.json()
    assert_test(
        "GET /health (PostGIS Connectivity)",
        res.status_code == 200 and data.get("status") == "healthy",
        f"- PostGIS: {data.get('postgis_version')}, POIs: {data.get('total_services_indexed')}"
    )

    # TEST 3: Categories flat list
    res = client.get("/api/v1/categories/")
    cats = res.json()
    assert_test("GET /api/v1/categories/ (Categories List)", res.status_code == 200 and len(cats) >= 20, f"Found {len(cats)} categories/subcategories")

    # TEST 4: Categories tree
    res = client.get("/api/v1/categories/tree")
    tree = res.json()
    assert_test("GET /api/v1/categories/tree (Category Tree)", res.status_code == 200 and len(tree) >= 8, f"Found {len(tree)} top-level categories")

    # TEST 5: Boundaries GeoJSON
    res = client.get("/api/v1/boundaries/")
    boundaries = res.json()
    assert_test(
        "GET /api/v1/boundaries/ (Municipal Polygons)",
        res.status_code == 200 and boundaries.get("type") == "FeatureCollection" and len(boundaries.get("features", [])) >= 2,
        f"Features: {len(boundaries.get('features', []))}"
    )

    # TEST 6: Nearby search (Pune Station 18.5284, 73.8744 - 3000m radius)
    res = client.get("/api/v1/services/nearby?lat=18.5284&lon=73.8744&radius_meters=3000&subcategory=Hospital")
    nearby = res.json()
    assert_test(
        "GET /api/v1/services/nearby (Hospitals within 3km of Pune Station)",
        res.status_code == 200 and nearby.get("total", 0) > 0,
        f"Found {len(nearby.get('items', []))} hospitals nearby (closest: {nearby['items'][0]['name'] if nearby.get('items') else 'N/A'} at {nearby['items'][0]['distance_meters'] if nearby.get('items') else 0}m)"
    )

    # TEST 7: KNN search (5 closest Petrol Pumps to Swargate: 18.5018, 73.8636)
    res = client.get("/api/v1/services/knn?lat=18.5018&lon=73.8636&k=5&subcategory=Petrol%20Pump")
    knn = res.json()
    assert_test(
        "GET /api/v1/services/knn (5 Closest Petrol Pumps to Swargate)",
        res.status_code == 200 and len(knn.get("items", [])) == 5,
        f"Returned {len(knn.get('items', []))} nearest POIs (closest: {knn['items'][0]['name'] if knn.get('items') else 'N/A'} at {knn['items'][0]['distance_meters'] if knn.get('items') else 0}m)"
    )

    # TEST 8: Text Search ('Ruby' hospital search)
    res = client.get("/api/v1/services/search?q=Ruby")
    search_res = res.json()
    assert_test(
        "GET /api/v1/services/search (Keyword Search 'Ruby')",
        res.status_code == 200 and search_res.get("total", 0) >= 1,
        f"Matches found: {search_res.get('total')}"
    )

    # TEST 9: Service detail by ID
    first_service_id = nearby["items"][0]["id"] if (nearby.get("items") and len(nearby["items"]) > 0) else 1
    res = client.get(f"/api/v1/services/{first_service_id}")
    detail = res.json()
    assert_test(
        f"GET /api/v1/services/{first_service_id} (Service Detail)",
        res.status_code == 200 and detail.get("id") == first_service_id,
        f"Name: {detail.get('name')}, Category: {detail.get('category')} / {detail.get('subcategory')}"
    )

    # TEST 10: GeoJSON FeatureCollection stream
    res = client.get("/api/v1/services/geojson?category=Emergency")
    geojson_out = res.json()
    assert_test(
        "GET /api/v1/services/geojson (Native PostGIS GeoJSON Stream)",
        res.status_code == 200 and geojson_out.get("type") == "FeatureCollection" and len(geojson_out.get("features", [])) > 0,
        f"Returned {len(geojson_out.get('features', []))} features in Emergency category"
    )

    # TEST 11: Analytics Overview
    res = client.get("/api/v1/analytics/overview")
    overview = res.json()
    assert_test(
        "GET /api/v1/analytics/overview (System Metrics)",
        res.status_code == 200 and overview.get("total_services") > 0,
        f"Total services: {overview.get('total_services')}, Municipalities: {len(overview.get('municipalities', []))}"
    )

    # TEST 12: Spatial Point-in-Polygon Density Analysis
    res = client.get("/api/v1/analytics/density")
    density = res.json()
    assert_test(
        "GET /api/v1/analytics/density (Spatial POI Density per km²)",
        res.status_code == 200 and len(density.get("boundaries", [])) >= 2,
        f"Overall Density: {density.get('overall_density_per_sqkm')} POIs/km²"
    )

    # TEST 13: Nearby Category Summary
    res = client.get("/api/v1/analytics/nearby-summary?lat=18.5204&lon=73.8567&radius_meters=2000")
    summary = res.json()
    assert_test(
        "GET /api/v1/analytics/nearby-summary (Category Breakdown within 2km)",
        res.status_code == 200 and summary.get("total_services_nearby") > 0,
        f"Found {summary.get('total_services_nearby')} total POIs across {len(summary.get('breakdown', []))} subcategories"
    )

    print("=" * 75)
    print(f">> TEST RESULTS: {tests_passed}/{total_tests} tests passed ({round(tests_passed/total_tests*100, 1)}%)")
    print("=" * 75)

    if tests_passed == total_tests:
        print("[SUCCESS] ALL FASTAPI SPATIAL ENDPOINTS ARE WORKING PERFECTLY!")
        return 0
    else:
        print("[WARNING] Some tests failed. Check logs above.")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)

import urllib.request
import json

u2 = 'http://127.0.0.1:8000/api/v1/services/nearby?lat=18.5204&lon=73.8567&radius_meters=2000&subcategory=Restaurant'
res2 = urllib.request.urlopen(u2)
d2 = json.loads(res2.read().decode())
print(f"Total Restaurants within 2km: {d2['total']}")
print(f"Closest Restaurant: {d2['items'][0]['name']} at {d2['items'][0]['distance_meters']}m")
print(f"Furthest Restaurant in 2km: {d2['items'][-1]['name']} at {d2['items'][-1]['distance_meters']}m")

u3 = 'http://127.0.0.1:8000/api/v1/services/nearby?lat=18.5204&lon=73.8567&radius_meters=3000&subcategory=Restaurant'
res3 = urllib.request.urlopen(u3)
d3 = json.loads(res3.read().decode())
print(f"\nTotal Restaurants within 3km: {d3['total']}")
print(f"Furthest Restaurant in 3km: {d3['items'][-1]['name']} at {d3['items'][-1]['distance_meters']}m")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_buses():
    response = client.get("/api/v1/buses/")
    assert response.status_code == 200
    buses = response.json()
    assert isinstance(buses, list)
    assert len(buses) > 0

def test_get_routes():
    response = client.get("/api/v1/routes/")
    assert response.status_code == 200
    routes = response.json()
    assert isinstance(routes, list)
    assert len(routes) > 0

def test_get_stops():
    response = client.get("/api/v1/stops/")
    assert response.status_code == 200
    stops = response.json()
    assert isinstance(stops, list)
    assert len(stops) > 0

def test_get_nearby_stops():
    response = client.get("/api/v1/stops/nearby?lat=12.9716&lng=77.5946&radius_km=10")
    assert response.status_code == 200
    nearby = response.json()
    assert isinstance(nearby, list)
    assert len(nearby) > 0

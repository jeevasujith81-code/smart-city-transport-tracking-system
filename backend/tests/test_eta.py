from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_eta_prediction():
    # Fetch first bus and stop
    bus_res = client.get("/api/v1/buses/")
    stop_res = client.get("/api/v1/stops/")
    
    assert bus_res.status_code == 200
    assert stop_res.status_code == 200
    
    buses = bus_res.json()
    stops = stop_res.json()
    
    bus_id = buses[0]["id"]
    stop_id = stops[0]["id"]
    
    eta_res = client.get(f"/api/v1/eta/{bus_id}/{stop_id}")
    assert eta_res.status_code == 200
    data = eta_res.json()
    assert "predicted_eta_minutes" in data
    assert "confidence_score" in data
    assert "formatted_eta" in data

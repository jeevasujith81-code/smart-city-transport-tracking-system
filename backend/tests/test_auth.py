import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_login_admin():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@citytrack.com", "password": "Admin@123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "ADMIN"

def test_login_invalid_password():
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@citytrack.com", "password": "WrongPassword"}
    )
    assert response.status_code == 401

def test_register_passenger():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newtestuser@citytrack.com",
            "password": "TestPassword123",
            "full_name": "Test Passenger",
            "role": "PASSENGER"
        }
    )
    assert response.status_code in [201, 400]  # 400 if already exists in repeated run

import pytest

def test_database_connection(db_connection_check):
    """Test that database connectivity is established and reachable."""
    assert db_connection_check is True

def test_api_ping(client):
    """Test the main API root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "OutfitAR"
    assert data["status"] == "online"

def test_api_health(client):
    """Test the API health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_health(client):
    response = client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_schema(client):
    response = client.get("/api/schema/")
    assert response.status_code == 200

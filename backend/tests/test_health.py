from __future__ import annotations


async def test_health_ok(client) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["redis"] == "ok"


async def test_openapi_served(client) -> None:
    resp = await client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    assert "/api/v1/documents" in resp.json()["paths"]

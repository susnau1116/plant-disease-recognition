def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["classes"] == 38
    assert data["diseases"] == 38
    assert data["faqs"] >= 36
    assert data["model"].endswith(".onnx")


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "docs" in resp.json()

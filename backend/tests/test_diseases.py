def test_crops(client):
    resp = client.get("/api/crops")
    assert resp.status_code == 200
    crops = resp.json()
    assert len(crops) == 14
    assert sum(c["total"] for c in crops) == 38


def test_list_diseases(client):
    resp = client.get("/api/diseases", params={"page_size": 100})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 38
    assert len(data["items"]) == 38


def test_search_diseases(client):
    resp = client.get("/api/diseases", params={"q": "晚疫病"})
    data = resp.json()
    assert data["total"] >= 2
    assert all("晚疫病" in i["name_cn"] for i in data["items"])


def test_filter_by_crop(client):
    resp = client.get("/api/diseases", params={"crop": "番茄", "page_size": 100})
    data = resp.json()
    assert data["total"] == 10


def test_disease_detail(client):
    resp = client.get("/api/diseases/Tomato___Late_blight")
    assert resp.status_code == 200
    d = resp.json()
    assert d["name_cn"] == "番茄晚疫病"
    assert d["healthy"] is False
    assert len(d["treatments"]) >= 2
    t = d["treatments"][0]
    for field in ("type", "name", "expected_effect", "effect_time", "judgement", "fallback"):
        assert t[field] is not None


def test_disease_examples(client):
    resp = client.get("/api/diseases/Tomato___Late_blight")
    d = resp.json()
    assert len(d["examples"]) >= 2
    assert all("/static/examples/Tomato___Late_blight/" in url for url in d["examples"])
    img = client.get(d["examples"][0].replace("http://testserver", ""))
    assert img.status_code == 200
    assert img.headers["content-type"].startswith("image/")


def test_disease_detail_404(client):
    resp = client.get("/api/diseases/Not___Exist")
    assert resp.status_code == 404


def test_healthy_disease(client):
    resp = client.get("/api/diseases/Apple___healthy")
    d = resp.json()
    assert d["healthy"] is True
    assert len(d["treatments"]) >= 1

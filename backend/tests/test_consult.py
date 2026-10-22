def test_faq_list(client):
    resp = client.get("/api/faqs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 36
    assert "病害识别" in data["categories"]


def test_consult_matched(client):
    resp = client.post("/api/consult", json={"question": "白粉病怎么防治？"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["matched"] is True
    assert data["answer"]["category"] == "防治方法"
    assert "白粉病" in data["answer"]["question"]


def test_consult_keyword(client):
    resp = client.post("/api/consult", json={"question": "叶背有白霉是什么病"})
    data = resp.json()
    assert data["matched"] is True
    assert "晚疫病" in data["answer"]["answer"] or "霜霉" in data["answer"]["answer"]


def test_consult_unmatched(client):
    resp = client.post("/api/consult", json={"question": "今天天气怎么样"})
    data = resp.json()
    assert data["matched"] is False
    assert data["suggestion"]

import pytest

from app import database as db


@pytest.fixture
def message_ids():
    ids = []
    yield ids
    if ids:
        with db.connect() as conn:
            placeholders = ",".join("?" for _ in ids)
            conn.execute(f"DELETE FROM messages WHERE id IN ({placeholders})", ids)


def _create(client, message_ids, question="测试留言：葡萄霜霉病怎么防治？", contact=None):
    payload = {"question": question}
    if contact is not None:
        payload["contact"] = contact
    resp = client.post("/api/messages", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    message_ids.append(data["id"])
    return data


def test_create_message(client, message_ids):
    data = _create(client, message_ids, contact="13800000000")
    assert data["status"] == "pending"
    assert data["reply"] is None
    assert data["contact"] == "13800000000"
    assert data["created_at"]


def test_create_message_validation(client, message_ids):
    assert client.post("/api/messages", json={"question": ""}).status_code == 422
    assert client.post("/api/messages", json={"question": "   "}).status_code == 422


def test_list_messages(client, message_ids):
    first = _create(client, message_ids, question="测试留言甲")
    second = _create(client, message_ids, question="测试留言乙")
    ids = f"{first['id']},{second['id']}"

    resp = client.get("/api/messages", params={"ids": ids})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert {item["question"] for item in data["items"]} == {"测试留言甲", "测试留言乙"}

    pending = client.get("/api/messages", params={"ids": ids, "status": "pending"}).json()
    assert pending["total"] == 2


def test_reply_message(client, message_ids):
    created = _create(client, message_ids)
    resp = client.post(
        f"/api/messages/{created['id']}/reply",
        json={"reply": "可用烯酰吗啉或霜脲氰防治，注意轮换用药。"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "replied"
    assert data["reply"].startswith("可用烯酰吗啉")
    assert data["replied_at"]

    detail = client.get(f"/api/messages/{created['id']}").json()
    assert detail["status"] == "replied"

    replied = client.get(
        "/api/messages", params={"ids": str(created["id"]), "status": "replied"}
    ).json()
    assert replied["total"] == 1


def test_message_not_found(client):
    assert client.get("/api/messages/99999999").status_code == 404
    assert (
        client.post("/api/messages/99999999/reply", json={"reply": "测试"}).status_code
        == 404
    )


def test_list_invalid_status(client):
    assert client.get("/api/messages", params={"status": "bad"}).status_code == 422

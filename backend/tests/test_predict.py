"""识别接口端到端测试：用 PlantVillage 测试集真实图片验证类别与置信度。"""

from app import config


def _first_per_class(splits, n=6):
    seen = {}
    for rel, idx in splits["test"]:
        if idx not in seen:
            seen[idx] = rel
        if len(seen) >= n:
            break
    return list(seen.items())


def test_class_order_matches_training(splits):
    assert splits["classes"] == config.load_classes()


def test_predict_known_images(client, splits, dataset_root):
    classes = splits["classes"]
    for idx, rel in _first_per_class(splits):
        path = dataset_root / rel
        assert path.exists(), f"测试图片不存在: {path}"
        content = path.read_bytes()
        resp = client.post(
            "/api/predict", files={"file": (path.name, content, "image/jpeg")}
        )
        assert resp.status_code == 200, f"{path.name}: {resp.text}"
        data = resp.json()
        assert data["class_name"] == classes[idx], (
            f"{path.name}: 预测 {data['class_name']} != 标注 {classes[idx]}"
        )
        assert data["confidence"] > 0.5
        assert data["top_k"][0]["class_name"] == data["class_name"]
        assert data["disease"]["treatments"]
        assert data["inference_ms"] > 0


def test_predict_rejects_invalid_file(client):
    resp = client.post(
        "/api/predict", files={"file": ("a.txt", b"not an image", "text/plain")}
    )
    assert resp.status_code == 400

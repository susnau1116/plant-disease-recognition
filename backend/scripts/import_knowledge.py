"""知识库导入：backend/data/diseases/*.json + faq.json → SQLite。

用法（在 backend 目录下）：
    python scripts/import_knowledge.py            # 重建知识库
    python -m scripts.import_knowledge            # 同上

注意：修改 backend/data 下的 JSON 后需重新执行本脚本（或删除 database/app.db 后重启服务自动导入）。
"""

import glob
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import config  # noqa: E402
from app.database import SCHEMA, connect  # noqa: E402


def load_disease_files():
    files = sorted(glob.glob(str(config.DATA_DIR / "diseases" / "*.json")))
    if not files:
        raise FileNotFoundError(f"未找到病害数据文件: {config.DATA_DIR / 'diseases'}")
    crops = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            crops.append(json.load(f))
    return crops


def load_faq_file():
    path = config.DATA_DIR / "faq.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def import_all(conn, verbose=True):
    """在给定连接中重建知识库，返回统计信息。"""
    classes = config.load_classes()
    crops = load_disease_files()
    faq_data = load_faq_file()

    rows = []
    for crop in crops:
        for d in crop["diseases"]:
            rows.append(
                (
                    d["class_name"],
                    crop["crop"],
                    crop.get("crop_en"),
                    d.get("name_cn", ""),
                    d.get("name_en"),
                    1 if d.get("healthy") else 0,
                    d.get("symptoms"),
                    d.get("occurrence"),
                    d.get("transmission"),
                )
            )

    from_rows = {r[0] for r in rows}
    missing = [c for c in classes if c not in from_rows]
    extra = [c for c in from_rows if c not in classes]
    if missing or extra:
        raise ValueError(f"知识库与类别文件不一致：缺少 {missing}，多余 {extra}")

    conn.execute("DELETE FROM treatments")
    conn.execute("DELETE FROM diseases")
    conn.execute("DELETE FROM faqs")

    conn.executemany(
        """
        INSERT INTO diseases
        (class_name, crop, crop_en, name_cn, name_en, healthy, symptoms, occurrence, transmission)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    treatment_rows = []
    for crop in crops:
        for d in crop["diseases"]:
            for order, t in enumerate(d.get("treatments", [])):
                treatment_rows.append(
                    (
                        d["class_name"],
                        t.get("type", ""),
                        t.get("name", ""),
                        t.get("formulation"),
                        t.get("dosage"),
                        t.get("usage"),
                        t.get("precautions"),
                        t.get("expected_effect"),
                        t.get("effect_time"),
                        t.get("judgement"),
                        t.get("fallback"),
                        order,
                    )
                )
    conn.executemany(
        """
        INSERT INTO treatments
        (class_name, type, name, formulation, dosage, usage, precautions,
         expected_effect, effect_time, judgement, fallback, sort_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        treatment_rows,
    )

    faq_rows = [
        (
            f["id"],
            f["category"],
            f["question"],
            f["answer"],
            json.dumps(f.get("keywords", []), ensure_ascii=False),
        )
        for f in faq_data["faqs"]
    ]
    conn.executemany(
        "INSERT INTO faqs (id, category, question, answer, keywords) VALUES (?, ?, ?, ?, ?)",
        faq_rows,
    )

    stats = {"diseases": len(rows), "treatments": len(treatment_rows), "faqs": len(faq_rows)}
    if verbose:
        print(
            f"导入完成：病害 {stats['diseases']} 类 / 防治方案 {stats['treatments']} 条 / "
            f"FAQ {stats['faqs']} 条 → {config.DB_PATH}"
        )
    return stats


def ensure_imported():
    """若数据库为空则自动导入（供应用启动时调用）。"""
    from app import database as db

    db.init_db()
    if db.count("diseases") == 0:
        with connect() as conn:
            import_all(conn, verbose=False)


def main():
    from app.database import init_db

    init_db()
    with connect() as conn:
        import_all(conn, verbose=True)


if __name__ == "__main__":
    main()

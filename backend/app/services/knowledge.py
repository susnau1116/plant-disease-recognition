"""病害知识库查询：病害列表/详情、防治方案、作物统计。

知识库为只读静态数据，查询结果用 lru_cache 缓存在进程内；
修改 JSON / 重新导入 SQLite 后需重启服务（或调用 clear_cache）。
"""

import copy
from functools import lru_cache
from typing import Optional

from .. import config
from .. import database as db


@lru_cache(maxsize=1)
def _crops_cached():
    rows = db.query(
        """
        SELECT crop, crop_en,
               COUNT(*) AS total,
               SUM(CASE WHEN healthy = 1 THEN 1 ELSE 0 END) AS healthy,
               SUM(CASE WHEN healthy = 0 THEN 1 ELSE 0 END) AS diseased
        FROM diseases
        GROUP BY crop, crop_en
        ORDER BY total DESC, crop
        """
    )
    return tuple(
        {
            "crop": r["crop"],
            "crop_en": r["crop_en"],
            "total": r["total"],
            "healthy": r["healthy"] or 0,
            "diseased": r["diseased"] or 0,
        }
        for r in rows
    )


def list_crops():
    return [dict(item) for item in _crops_cached()]


def list_diseases(
    crop: Optional[str] = None,
    q: Optional[str] = None,
    healthy: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
):
    where, params = [], []
    if crop:
        where.append("crop = ?")
        params.append(crop)
    if healthy is not None:
        where.append("healthy = ?")
        params.append(1 if healthy else 0)
    if q:
        where.append("(name_cn LIKE ? OR name_en LIKE ? OR class_name LIKE ? OR symptoms LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like, like])
    cond = f"WHERE {' AND '.join(where)}" if where else ""

    total = db.query_one(f"SELECT COUNT(*) AS n FROM diseases {cond}", params)["n"]
    rows = db.query(
        f"""
        SELECT class_name, crop, crop_en, name_cn, name_en, healthy, symptoms
        FROM diseases {cond}
        ORDER BY crop, healthy, name_cn
        LIMIT ? OFFSET ?
        """,
        [*params, page_size, (page - 1) * page_size],
    )
    for r in rows:
        r["healthy"] = bool(r["healthy"])
    return total, rows


@lru_cache(maxsize=64)
def _example_files(class_name: str):
    folder = config.EXAMPLES_DIR / class_name
    if not folder.is_dir():
        return ()
    return tuple(
        sorted(
            p.name
            for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in config.ALLOWED_SUFFIXES
        )
    )


def get_examples(class_name: str, base_url: str = ""):
    """返回类别例图 URL 列表（来自 static/examples/<class_name>/），无例图则空列表。"""
    base = base_url.rstrip("/")
    return [
        f"{base}/static/examples/{class_name}/{name}"
        for name in _example_files(class_name)
    ]


@lru_cache(maxsize=64)
def _disease_cached(class_name: str):
    disease = db.query_one("SELECT * FROM diseases WHERE class_name = ?", (class_name,))
    if not disease:
        return None
    disease["healthy"] = bool(disease["healthy"])
    treatments = db.query(
        "SELECT * FROM treatments WHERE class_name = ? ORDER BY sort_order, id", (class_name,)
    )
    for t in treatments:
        t.pop("class_name", None)
        t.pop("sort_order", None)
        t.pop("id", None)
    disease["treatments"] = treatments
    return disease


def get_disease(class_name: str, base_url: str = ""):
    cached = _disease_cached(class_name)
    if cached is None:
        return None
    disease = copy.deepcopy(cached)
    disease["examples"] = get_examples(class_name, base_url)
    return disease


@lru_cache(maxsize=1)
def _briefs_cached():
    rows = db.query(
        "SELECT class_name, crop, crop_en, name_cn, name_en, healthy, symptoms "
        "FROM diseases"
    )
    return {
        r["class_name"]: {
            **r,
            "healthy": bool(r["healthy"]),
        }
        for r in rows
    }


def get_briefs(class_names):
    """按类别名批量获取简要信息（用于 top-k 展示）。"""
    if not class_names:
        return {}
    briefs = _briefs_cached()
    return {name: dict(briefs[name]) for name in class_names if name in briefs}


@lru_cache(maxsize=16)
def _faqs_cached(category: Optional[str] = None):
    if category:
        rows = db.query(
            "SELECT * FROM faqs WHERE category = ? ORDER BY id", (category,)
        )
    else:
        rows = db.query("SELECT * FROM faqs ORDER BY id")
    return tuple(_faq_row(r) for r in rows)


def list_faqs(category: Optional[str] = None):
    return [dict(item) for item in _faqs_cached(category)]


@lru_cache(maxsize=1)
def _categories_cached():
    rows = db.query("SELECT category FROM faqs GROUP BY category ORDER BY MIN(id)")
    return tuple(r["category"] for r in rows)


def get_categories():
    return list(_categories_cached())


@lru_cache(maxsize=1)
def _stats_cached():
    return {
        "diseases": db.count("diseases"),
        "treatments": db.count("treatments"),
        "faqs": db.count("faqs"),
    }


def stats():
    return dict(_stats_cached())


def clear_cache():
    """知识库数据重新导入后调用，清空进程内缓存。"""
    for fn in (
        _crops_cached,
        _example_files,
        _disease_cached,
        _briefs_cached,
        _faqs_cached,
        _categories_cached,
        _stats_cached,
    ):
        fn.cache_clear()


def _faq_row(r):
    import json

    return {
        "id": r["id"],
        "category": r["category"],
        "question": r["question"],
        "answer": r["answer"],
        "keywords": json.loads(r["keywords"] or "[]"),
    }

"""SQLite 数据库访问（标准库 sqlite3，无额外 ORM 依赖）。"""

import sqlite3
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS diseases (
    class_name   TEXT PRIMARY KEY,
    crop         TEXT NOT NULL,
    crop_en      TEXT,
    name_cn      TEXT NOT NULL,
    name_en      TEXT,
    healthy      INTEGER NOT NULL DEFAULT 0,
    symptoms     TEXT,
    occurrence   TEXT,
    transmission TEXT
);

CREATE TABLE IF NOT EXISTS treatments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    class_name      TEXT NOT NULL REFERENCES diseases(class_name) ON DELETE CASCADE,
    type            TEXT NOT NULL,
    name            TEXT NOT NULL,
    formulation     TEXT,
    dosage          TEXT,
    usage           TEXT,
    precautions     TEXT,
    expected_effect TEXT,
    effect_time     TEXT,
    judgement       TEXT,
    fallback        TEXT,
    sort_order      INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_treatments_class ON treatments(class_name);

CREATE TABLE IF NOT EXISTS faqs (
    id       INTEGER PRIMARY KEY,
    category TEXT NOT NULL,
    question TEXT NOT NULL,
    answer   TEXT NOT NULL,
    keywords TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_faqs_category ON faqs(category);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    question   TEXT NOT NULL,
    contact    TEXT,
    status     TEXT NOT NULL DEFAULT 'pending',
    reply      TEXT,
    created_at TEXT NOT NULL,
    replied_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(status);
"""


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def query(sql, params=()):
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def query_one(sql, params=()):
    with connect() as conn:
        row = conn.execute(sql, params).fetchone()
    return dict(row) if row else None


def count(table):
    row = query_one(f"SELECT COUNT(*) AS n FROM {table}")
    return row["n"] if row else 0

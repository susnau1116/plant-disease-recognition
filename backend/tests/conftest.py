import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

SPLITS_FILE = (
    Path(__file__).resolve().parents[2]
    / "model"
    / "data"
    / "splits"
    / "plantvillage_r70_15_15_seed42.json"
)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def splits():
    with open(SPLITS_FILE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def dataset_root(splits):
    return Path(splits["root"])

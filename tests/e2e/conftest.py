"""E2E tests run the FastAPI app on a private, temporary data dir with a fixed date and the rule provider ($0, offline)."""
from __future__ import annotations

import os
import tempfile

import pytest

os.environ["UDIP_DATA_DIR"] = tempfile.mkdtemp(prefix="udip_e2e_")
os.environ["UDIP_TODAY"] = "2026-11-22"
os.environ["UDIP_PROVIDER"] = "rules"
os.environ["UDIP_JOBS_SYNC"] = "1"


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient on a fresh, empty data dir (the store seeds the UMB demo cases and archive on first use)."""
    from fastapi.testclient import TestClient

    from app import store
    from app.main import app
    from udip import config

    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("UDIP_TODAY", "2026-11-22")
    monkeypatch.setenv("UDIP_PROVIDER", "rules")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    store.reset_backend()
    assert config.data_dir().resolve() == tmp_path.resolve()
    yield TestClient(app)
    store.reset_backend()

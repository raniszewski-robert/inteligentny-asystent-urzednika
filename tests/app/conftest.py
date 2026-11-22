"""App tests run on a private data dir (fresh SQLite per test session) with a fixed date."""
from __future__ import annotations

import os
import tempfile

import pytest

_TMP = tempfile.mkdtemp(prefix="udip_app_test_")
os.environ["UDIP_DATA_DIR"] = _TMP
os.environ["UDIP_TODAY"] = "2026-11-22"
os.environ["UDIP_PROVIDER"] = "rules"
os.environ["UDIP_JOBS_SYNC"] = "1"  # Bielik jobs run inline in tests


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """A new empty data dir for one test (the store seeds the 10 UMB demo cases on first use)."""
    from app import store
    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path))
    store.reset_backend()
    yield tmp_path
    store.reset_backend()

"""Shared test setup: every test gets its own empty data dir (SQLite + stored audio)."""
import pytest

from app import config


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "data" / "app.db")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://example.test")
    yield tmp_path

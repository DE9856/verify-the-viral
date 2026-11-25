"""Lane A · A4/A5: web server routes, result page, PWA files, share target."""
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app import config
from app.api import app
from app.core import aletheia
from tests.test_cache import FakeAletheia

AUDIO = Path(__file__).resolve().parent.parent / "research" / "test-audio"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", "")
    monkeypatch.setattr(config, "DETECTIF_API_KEY", "test-key")
    fake = FakeAletheia()
    aletheia.use_transport(httpx.MockTransport(fake))
    yield fake
    aletheia.use_transport(None)


def upload(client, url, name="spliced_en.wav", field="file", **kw):
    with open(AUDIO / name, "rb") as f:
        return client.post(url, files={field: (name, f, "audio/wav")}, **kw)


def test_api_check_returns_contract_json(client, live):
    r = upload(client, "/api/check").json()
    assert r["band"] == "partly_fake" and r["core_regions"] == [[10.0, 14.0]]
    assert client.get(f"/api/result/{r['id']}").json()["id"] == r["id"]


def test_share_target_redirects_to_result_page(client, live):
    resp = upload(client, "/share", field="media", follow_redirects=False)
    assert resp.status_code == 303 and resp.headers["location"].startswith("/r/")
    page = client.get(resp.headers["location"] + "?lang=kn")
    assert page.status_code == 200 and '"band": "partly_fake"' in page.text and 'lang="kn"' in page.text
    assert "wavesurfer-7.12.12" in page.text


def test_media_serves_the_checked_audio(client, live):
    r = upload(client, "/api/check").json()
    m = client.get(f"/media/{r['id']}")
    assert m.status_code == 200 and m.content == (AUDIO / "spliced_en.wav").read_bytes()


def test_feedback_endpoint(client, live):
    r = upload(client, "/api/check").json()
    assert client.post(f"/api/feedback/{r['id']}", json={"correct": True}).json() == {"ok": True}
    assert live.feedback == [{"correct": True}]
    assert client.post("/api/feedback/nope", json={"correct": True}).status_code == 404


def test_unknown_result_is_404(client):
    assert client.get("/r/doesnotexist").status_code == 404
    assert client.get("/api/result/doesnotexist").status_code == 404
    assert client.get("/media/doesnotexist").status_code == 404


def test_mock_mode_result_page_works(client, monkeypatch):
    monkeypatch.setattr(config, "MOCK_ALETHEIA", "fake_kn")
    r = upload(client, "/api/check").json()
    assert r["band"] == "likely_fake"
    assert client.get(f"/r/{r['id']}").status_code == 200
    assert client.get(f"/media/{r['id']}").status_code == 200          # the fixture's real audio


def test_pwa_files(client):
    m = client.get("/manifest.webmanifest")
    assert m.headers["content-type"].startswith("application/manifest+json")
    st = m.json()["share_target"]
    assert st["action"] == "/share" and st["method"] == "POST" and st["params"]["files"][0]["name"] == "media"
    for icon in m.json()["icons"]:
        assert client.get(icon["src"]).status_code == 200
    sw = client.get("/sw.js")
    assert sw.status_code == 200 and "javascript" in sw.headers["content-type"]
    assert client.get("/offline").status_code == 200
    assert 'rel="manifest"' in client.get("/").text


def test_health_reports_problems(client, live, monkeypatch):
    monkeypatch.setattr(config, "DETECTIF_API_KEY", "")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "http://localhost:8000")
    h = client.get("/health").json()
    assert h["mode"] == "live" and not h["ok"] and h["detectif"]["status"] == "ok"
    assert any("DETECTIF_API_KEY" in i for i in h["issues"]) and any("localhost" in i for i in h["issues"])

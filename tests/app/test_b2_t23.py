"""T23: LLM features in the UI. Rules by default; local Bielik only when .env enables it and its server answers.
Rules → no LLM elements; a faked model → badges bound to the real results ($0, offline)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import udip.llm as L
from app.main import app
from tests.app._b2_seed import isolate, seed_543
from udip.llm_tasks import analysis, anonymization, drafting, routing


@pytest.fixture()
def client(tmp_path, monkeypatch):
    isolate(tmp_path, monkeypatch)
    c = TestClient(app)
    c.cid = seed_543()
    return c


@pytest.fixture()
def model_on(monkeypatch):
    from app import settings
    monkeypatch.setattr(L, "available", lambda provider=None: True)
    monkeypatch.setattr(settings, "_server_up", lambda: True)
    monkeypatch.setenv("UDIP_PROVIDER", "openai_compat:bielik")


def test_rules_only_shows_no_llm_elements(client):
    assert client.get("/ustawienia").status_code == 404  # no settings screen: rules + Bielik always
    for url in (f"/sprawy/{client.cid}/projekt", f"/sprawy/{client.cid}/anonimizacja"):
        page = client.get(url).text
        assert 'id="btn-model"' not in page and 'id="badge-llm"' not in page, url
    assert 'id="badge-analiza"' not in client.get(f"/sprawy/{client.cid}").text


def test_rules_by_default_bielik_only_from_env(client, monkeypatch):
    from app import settings
    monkeypatch.delenv("UDIP_PROVIDER", raising=False)
    assert settings.provider_choice() == "rules" and settings.effective() == "rules"
    monkeypatch.setenv("UDIP_PROVIDER", "openai_compat:bielik")
    monkeypatch.setattr(settings, "_server_up", lambda: False)
    assert settings.effective() == "rules" and not settings.llm_on()
    monkeypatch.setattr(settings, "_server_up", lambda: True)
    monkeypatch.setattr(L, "available", lambda provider=None: True)
    assert settings.effective() == "openai_compat:bielik" and settings.llm_on()
    for cloud in ("anthropic:haiku", "anthropic:sonnet"):  # only local models, ever
        monkeypatch.setenv("UDIP_PROVIDER", cloud)
        assert settings.provider_choice() == "rules"
    monkeypatch.setenv("UDIP_PROVIDER", "rules")
    assert settings.effective() == "rules"


def test_server_check_is_quick_and_cached(monkeypatch):
    import time
    from app import settings
    monkeypatch.setattr(L, "TRANSPORT", None)
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9/v1")  # nothing listens on port 9
    settings._ping.update(base=None, at=0.0, up=False)
    t0 = time.monotonic()
    assert settings._server_up() is False and settings._server_up() is False
    assert time.monotonic() - t0 < 3


def test_draft_with_model_badge_ok_and_rejected(client, model_on, monkeypatch):
    url = f"/sprawy/{client.cid}/projekt"
    assert 'id="btn-model"' in client.get(url).text
    monkeypatch.setattr(drafting, "paragraphs_llm", lambda qs, a, provider=None: [
        {"no": i + 1, "text": t or "Brak odpowiedzi.", "sources": [s]} for i, (s, t) in enumerate(a)])
    r = client.post(url, data={"action": "generuj", "mode": "llm", "ltype": "udostepnienie"}, follow_redirects=True)
    assert "Kontrola liczb: zgodne z odpowiedziami wydziałów" in r.text
    monkeypatch.setattr(drafting, "paragraphs_llm", lambda qs, a, provider=None: [
        {"no": i + 1, "text": "Wydano 999 999 zł.", "sources": []} for i in range(len(qs))])
    r = client.post(url, data={"mode": "llm", "ltype": "udostepnienie"}, follow_redirects=True)
    assert "Odrzucono akapity modelu" in r.text and "839 psom" in r.text  # template paragraphs kept


def test_anonymization_model_pass_adds_review_spans(client, model_on, monkeypatch):
    url = f"/sprawy/{client.cid}/anonimizacja"
    page = client.get(url).text
    assert 'id="btn-model"' in page
    from app import b2_store
    text = b2_store.get_draft(client.cid)["text"]
    i = text.index("Schronisko")
    monkeypatch.setattr(anonymization, "spans_llm", lambda t, provider=None: [
        {"start": i, "end": i + len("Schronisko"), "type": "OSOBA", "confidence": 0.6, "reason": "test"}])
    r = client.post(url, data={"action": "model"}, follow_redirects=True)
    assert 'class="tag tag-llm"' in r.text and "sp-llm" in r.text and 'id="badge-llm"' in r.text
    sp = [s for s in b2_store.get_draft(client.cid)["spans"] if s.get("source") == "llm"]
    assert len(sp) == 1 and sp[0]["status"] == "review"
    r = client.post(url, data={"action": "model"}, follow_redirects=True)  # second pass adds nothing new
    assert len([s for s in b2_store.get_draft(client.cid)["spans"] if s.get("source") == "llm"]) == 1


def test_analysis_badge_from_real_result(client, model_on, monkeypatch):
    monkeypatch.setattr(analysis, "analyze_llm", lambda t, provider=None: {
        "questions": [], "mode": "udip", "flags": [], "summary": "Koszty schroniska w 2025 r.", "applicant_type": "organizacja"})
    monkeypatch.setattr(routing, "route_llm", lambda q, deps, provider=None: None)
    r = client.post("/wniosek/nowy", data={"akcja": "analizuj", "tekst": "1. Ile kosztowało schronisko w 2025 r.?\n2. Ile psów adoptowano?"})
    assert 'id="badge-analiza"' in r.text and "Koszty schroniska" in r.text

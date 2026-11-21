"""T23: LLM features in the UI. Rules only → no LLM elements; a faked model → badges bound to the real results ($0, offline)."""
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
    monkeypatch.setattr(L, "available", lambda provider=None: True)
    monkeypatch.setenv("UDIP_PROVIDER", "openai_compat:bielik")


def test_rules_only_shows_no_llm_elements(client):
    s = client.get("/ustawienia").text
    assert "Model niedostępny – wyniki z reguł" in s
    assert "Anthropic" not in s and "Claude" not in s
    for url in (f"/sprawy/{client.cid}/projekt", f"/sprawy/{client.cid}/anonimizacja"):
        page = client.get(url).text
        assert 'id="btn-model"' not in page and 'id="badge-llm"' not in page, url
    assert 'id="badge-analiza"' not in client.get(f"/sprawy/{client.cid}").text


def test_settings_allows_only_rules_and_local_bielik(client, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "")
    monkeypatch.setenv("LLM_MODEL", "")
    from app import settings
    r = client.post("/ustawienia", data={"provider": "anthropic:haiku"}, follow_redirects=True)
    assert "Zapisano wybór modelu" in r.text
    assert settings.provider_choice() == "rules" and settings.effective() == "rules"
    r = client.post("/ustawienia", data={"provider": "openai_compat"}, follow_redirects=True)
    assert "Zapisano wybór modelu" in r.text and "LLM_BASE_URL" in r.text
    assert settings.provider_choice() == "openai_compat:local" and settings.effective() == "rules"


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


def test_settings_shows_mode(client, monkeypatch):
    monkeypatch.setenv("UDIP_OFFLINE", "1")
    s = client.get("/ustawienia").text
    assert 'id="tryb"' in s and "Bez internetu – reguły" in s and "UDIP_OFFLINE=1" in s

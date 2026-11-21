"""Lane C test helpers: every test gets its own cache/usage dir, a fake key and a fake transport (no network)."""
from __future__ import annotations

import json

import pytest

import udip.llm as L


class FakeTransport:
    """Returns queued answers (dict → JSON text, str → raw text) or answer(system, user, schema) when callable."""

    def __init__(self, answers=None, input_tokens=1000, output_tokens=200):
        self.answers = list(answers or [])
        self.calls: list[dict] = []
        self.it, self.ot = input_tokens, output_tokens

    def __call__(self, provider, model, system, user, schema, max_tokens, timeout):
        self.calls.append({"provider": provider, "model": model, "system": system, "user": user, "schema": schema})
        a = self.answers.pop(0) if len(self.answers) > 1 else (self.answers[0] if self.answers else {})
        if callable(a):
            a = a(system, user, schema)
        if isinstance(a, Exception):
            raise a
        text = a if isinstance(a, str) else json.dumps(a, ensure_ascii=False)
        return {"text": text, "input_tokens": self.it, "output_tokens": self.ot}


@pytest.fixture
def iso(tmp_path, monkeypatch):
    monkeypatch.setenv("UDIP_DATA_DIR", str(tmp_path / "var"))
    monkeypatch.setenv("UDIP_LLM_CACHE_DIR", str(tmp_path / "var" / "llm_cache"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("LLM_BUDGET_USD", "15")
    monkeypatch.setenv("UDIP_PROVIDER", "anthropic:sonnet")
    monkeypatch.setenv("UDIP_LLM_TAG", "test")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    yield tmp_path
    L.set_transport(None)


@pytest.fixture
def fake(iso):
    def make(*answers, **kw):
        t = FakeTransport(answers, **kw)
        L.set_transport(t)
        return t
    return make

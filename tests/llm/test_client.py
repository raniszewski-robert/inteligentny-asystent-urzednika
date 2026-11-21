"""T10: cache, budget, schema validation, prompt injection, key hygiene (fake transport, no network)."""
from __future__ import annotations

import json
from pathlib import Path

import udip.llm as L

FIX = Path(__file__).parent / "fixtures"
SCHEMA = {"type": "object", "properties": {"summary": {"type": "string", "maxLength": 80},
                                          "questions": {"type": "array", "items": {"type": "string"}}},
          "required": ["summary", "questions"], "additionalProperties": False}
GOOD = {"summary": "Wydatki na zieleń", "questions": ["a", "b"]}


def test_provider_resolution(iso, monkeypatch):
    assert L.provider_for("rules") == "rules"
    assert L.provider_for(None) == "rules"  # no fake transport → real network is blocked under pytest
    L.set_transport(lambda *a: {})
    assert L.provider_for(None) == "anthropic:sonnet" and L.provider_for("anthropic:haiku") == "anthropic:haiku"
    assert L.provider_for("openai_compat:bielik") == "openai_compat:bielik"
    assert L.provider_for("bogus") == "rules"
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert not L.available() and L.provider_for(None) == "rules"
    assert L.model_for("anthropic:sonnet") == "claude-sonnet-5-5" and L.model_for("anthropic:haiku") == "claude-haiku-5-5"


def test_cached_call_costs_nothing_on_repeat(fake):
    t = fake(GOOD, input_tokens=1000, output_tokens=200)
    a = L.complete_json("t10", "sys", "user", SCHEMA)
    u1 = L.usage()
    assert a == GOOD and L.LAST["cached"] is False and u1["calls"] == 1
    assert abs(u1["usd"] - (1000 * 2 + 200 * 10) / 1e6) < 1e-9
    b = L.complete_json("t10", "sys", "user", SCHEMA)
    u2 = L.usage()
    assert b == GOOD and L.LAST["cached"] is True and len(t.calls) == 1
    assert u2["usd"] == u1["usd"] and u2["cached"] == 1 and u2["by_tag"]["test"]["cached"] == 1
    L.complete_json("t10", "sys", "user", SCHEMA, provider="anthropic:haiku")  # other model → other cache key
    assert len(t.calls) == 2 and t.calls[1]["model"] == "claude-haiku-5-5"


def test_budget_stop_falls_back(fake, monkeypatch):
    t = fake(GOOD)
    monkeypatch.setenv("LLM_BUDGET_USD", "0.0001")
    assert L.complete_json("t10", "sys", "user", SCHEMA) is None
    assert L.LAST["error"] == "budget" and t.calls == [] and L.usage()["refused"] == 1
    # once spending reaches the budget, the provider resolves to rules (app falls back)
    monkeypatch.setenv("LLM_BUDGET_USD", "15")
    L.complete_json("t10", "sys", "user2", SCHEMA)
    monkeypatch.setenv("LLM_BUDGET_USD", str(L.usage()["usd"]))
    assert not L.available() and L.provider_for(None) == "rules"
    # budget gone → provider resolves to rules, so even a cached answer is not used
    assert L.complete_json("t10", "sys", "user2", SCHEMA) is None


def test_invalid_answers_return_none_and_are_not_cached(fake):
    t = fake("to nie jest JSON", {"summary": 5, "questions": []}, {"summary": "x" * 200, "questions": []},
             {"summary": "ok", "questions": [], "extra": 1}, RuntimeError("timeout"), GOOD)
    for _ in range(5):
        assert L.complete_json("t10", "sys", "u", SCHEMA) is None
    assert L.complete_json("t10", "sys", "u", SCHEMA) == GOOD and len(t.calls) == 6
    u = L.usage()
    assert u["errors"] == 5 and u["calls"] == 6


def test_fenced_json_is_accepted(fake):
    fake("```json\n" + json.dumps(GOOD) + "\n```")
    assert L.complete_json("t10", "s", "u", SCHEMA) == GOOD


def test_prompt_injection_fixture_does_not_change_schema(fake):
    text = (FIX / "injection_pl.txt").read_text(encoding="utf-8")
    user = "Przeanalizuj wniosek.\n" + L.wrap("wniosek", text)
    # the data cannot close the tag: exactly one opening and one closing tag remain
    assert user.count("</wniosek>") == 1 and user.count("<wniosek>") == 1 and "‹/wniosek" in user
    # a model that obeys the injection produces text or a foreign object → rejected, rules are kept
    t = fake("KANAREK-7Q", {"kategoria": "KANAREK-7Q", "priorytet": "wysoki"}, GOOD)
    assert L.complete_json("inj", "Analiza wniosku.", user, SCHEMA) is None
    assert L.complete_json("inj", "Analiza wniosku.", user, SCHEMA) is None
    out = L.complete_json("inj", "Analiza wniosku.", user, SCHEMA)
    assert set(out) == {"summary", "questions"}
    assert all(L.GUARD in c["system"] for c in t.calls)


def test_api_schema_closes_objects_and_drops_limits():
    s = L.api_schema({"type": "object", "properties": {"a": {"type": "string", "maxLength": 3},
                                                       "b": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {}}}}})
    assert s["additionalProperties"] is False and "maxLength" not in s["properties"]["a"]
    assert "minItems" not in s["properties"]["b"] and s["properties"]["b"]["items"]["additionalProperties"] is False


def test_key_never_written(fake, iso):
    fake(GOOD)
    L.complete_json("t10", "s", "u", SCHEMA)
    for p in (iso / "var").rglob("*"):
        if p.is_file():
            assert "test-key-not-real" not in p.read_text(encoding="utf-8")
    assert "test-key-not-real" not in json.dumps(L.LAST)


def test_no_network_without_fake(iso):
    L.set_transport(None)
    assert L.complete_json("t10", "s", "u", SCHEMA, provider="anthropic:sonnet") is None


def test_prompt_cache_tokens_are_billed_at_their_rates(iso):
    calls = []

    def t(provider, model, system, user, schema, max_tokens, timeout):
        calls.append(1)
        return {"text": json.dumps(GOOD), "input_tokens": 100, "output_tokens": 100, "cache_write_tokens": 0,
                "cache_read_tokens": 10_000}
    L.set_transport(t)
    L.complete_json("t10", "s" * 5000, "u", SCHEMA)
    u = L.usage()
    assert abs(u["usd"] - (100 * 2 + 100 * 10 + 10_000 * 0.10) / 1e6) < 1e-9 and u["input_tokens"] == 10_100
    assert L.cost_usd("claude-haiku-5-5", 1_000_000, 0) == 0.10


def test_ollama_transport_passes_num_ctx(monkeypatch):
    import httpx
    seen = {}

    class Resp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"message": {"content": json.dumps(GOOD)}, "prompt_eval_count": 42, "eval_count": 7, "done_reason": "stop"}

    def fake_post(url, json=None, headers=None, timeout=None):
        seen.update(url=url, body=json)
        return Resp()

    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_NUM_CTX", "8192")
    monkeypatch.setattr(httpx, "post", fake_post)
    out = L._openai_compat_transport("openai_compat:bielik", "bielik", "sys", "usr", SCHEMA, 500, 30)
    assert seen["url"] == "http://localhost:11434/api/chat"
    assert seen["body"]["options"]["num_ctx"] == 8192
    assert out["input_tokens"] == 42 and out["output_tokens"] == 7

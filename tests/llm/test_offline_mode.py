"""v2 T10: UDIP_OFFLINE=1 refuses every non-local model call; mode() names the active mode."""
import udip.llm as L


def test_offline_blocks_cloud(monkeypatch):
    monkeypatch.setenv("UDIP_OFFLINE", "1")
    monkeypatch.setattr(L, "available", lambda provider=None: True)
    monkeypatch.setattr(L, "_network_blocked", lambda: False)
    called = []
    monkeypatch.setattr(L, "_transport", lambda p: (lambda *a, **k: called.append(p)))
    assert L.complete_json("t", "s", "u", {"type": "object"}, provider="anthropic:sonnet") is None
    assert not called and "UDIP_OFFLINE" in L.LAST["error"]
    assert L.mode("anthropic:sonnet")["id"] == "offline_rules"


def test_local_bielik_allowed_offline(monkeypatch):
    monkeypatch.setenv("UDIP_OFFLINE", "1")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    m = L.mode("openai_compat:SpeakLeash/bielik-4.5b-v3.0-instruct:Q8_0")
    assert m["id"] == "offline_bielik" and m["network"] == "localhost"
    monkeypatch.setenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    assert not L._local_only("openai_compat:x")


def test_rules_mode_label(monkeypatch):
    monkeypatch.delenv("UDIP_OFFLINE", raising=False)
    assert L.mode("rules") == {"id": "offline_rules", "label": "Bez internetu – reguły", "network": "blocked"}

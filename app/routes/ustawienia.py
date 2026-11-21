"""Ustawienia (T23): local model choice (rules or Bielik/Ollama), availability and usage."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app import settings
from app.common import render
from udip import llm

router = APIRouter()


def _state() -> dict:
    choice = settings.provider_choice()
    eff = settings.effective()
    base = "openai_compat" if choice.startswith("openai_compat:") else (choice if choice == "rules" else "rules")
    return {"choice": base, "choice_raw": choice, "effective": eff, "llm_on": eff != "rules",
            "usage": llm.usage(), "choices": settings.CHOICES,
            "model_id": llm.model_for(eff) if eff != "rules" else eff,
            "mode": llm.mode(eff), "offline": llm.offline()}


@router.get("/ustawienia")
def ustawienia(request: Request, zapisano: int = 0):
    return render(request, "ustawienia.html", title="Ustawienia", saved=bool(zapisano), **_state())


@router.post("/ustawienia")
def ustawienia_post(provider: str = Form("rules")):
    settings.set_provider(provider)
    return RedirectResponse("/ustawienia?zapisano=1", status_code=303)

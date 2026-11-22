"""Stan zadań Bielika w tle: strona pyta co kilka sekund (htmx), a po zakończeniu dostaje wynik albo przeładowanie."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app import jobs, services
from app.common import is_htmx, render

router = APIRouter()


def context(job: dict | None) -> dict:
    """Zmienne dla app/templates/_bielik.html."""
    if not job:
        return {}
    from app import settings
    return {"model_job": job, "model_elapsed": jobs.elapsed(job), "model_names": services.department_names(),
            "model_name": settings.model_name(), "model_where": settings.model_where()}


@router.get("/model/{jid}")
def model_status(request: Request, jid: str):
    job = jobs.get(jid)
    if job is None:
        raise HTTPException(404)
    res = job.get("result") or {}
    if job["status"] == "done" and job["kind"] == "odswiez" and res.get("target") and is_htmx(request):
        return Response(status_code=200, headers={"HX-Redirect": res["target"]})
    return render(request, "_bielik.html", **context(job))

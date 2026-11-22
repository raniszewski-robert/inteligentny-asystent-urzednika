"""Verify Docker packaging files (Dockerfile, .dockerignore, docker-compose.yml, entrypoint)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_basics():
    df = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in df
    assert "tesseract-ocr-pol" in df
    assert "requirements.txt" in df
    assert "COPY app ./app" in df
    assert "COPY udip ./udip" in df
    assert "COPY scripts ./scripts" in df
    assert "COPY data-partner ./data-partner" in df
    assert "USER udip" in df
    assert "EXPOSE 8000" in df
    assert "HEALTHCHECK" in df
    assert "docker-entrypoint.sh" in df


def test_dockerignore_excludes_secrets_and_heavy_dirs():
    lines = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    for required in (".env", ".venv/", "var/", "video/", "demo-video-kit/", ".git/"):
        assert required in lines, f"{required} must be excluded in .dockerignore"


def test_docker_entrypoint_lf_and_commands():
    raw = (ROOT / "scripts" / "docker-entrypoint.sh").read_bytes()
    assert b"\r\n" not in raw, "docker-entrypoint.sh must use LF line endings"
    text = raw.decode("utf-8")
    assert text.startswith("#!/usr/bin/env sh\n")
    assert "scripts/seed.py" in text
    assert "uvicorn" in text


def test_docker_compose_mounts_data_volume():
    dc = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "asystent-udip:" in dc
    assert "udip_data:/data" in dc
    assert "host.docker.internal:host-gateway" in dc

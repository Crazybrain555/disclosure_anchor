"""Minimal FastAPI application."""

from __future__ import annotations

from disclosure_anchor.api.routers.health import router as health_router
from disclosure_anchor.adapters.runtime.doctor import render_report, run_doctor
from disclosure_anchor.domain.errors import ConfigurationError, MissingDependencyError
from disclosure_anchor.settings import Settings, load_settings

try:
    from fastapi import FastAPI
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local environment
    raise MissingDependencyError(
        "fastapi is not installed; install project dependencies before starting the API"
    ) from exc


def create_app(settings: Settings | None = None, *, validate_runtime: bool = True) -> FastAPI:
    if validate_runtime:
        resolved_settings = settings or load_settings()
        report = run_doctor(resolved_settings)
        if not report.ok:
            raise ConfigurationError(
                "runtime preflight failed:\n" + render_report(report.results)
            )

    app = FastAPI(title="disclosure_anchor", version="0.1.0")
    if health_router is not None:
        app.include_router(health_router)
    return app

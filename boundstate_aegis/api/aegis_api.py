#!/usr/bin/env python3
"""
Module: aegis_api
Purpose: AEGIS FastAPI application factory with route registration.
    Creates the main FastAPI app with CORS middleware and registers
    all AEGIS API routes for pathway, regulation, and assessment endpoints.

    Rev History:
        1.0.0 - Initial API factory with route registration

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from boundstate_aegis.api.routes import (
    assess_route,
    pathway_route,
    regulation_route,
    fate_route,
    litigation_route,
    portfolio_route,
    regulatory_v1_route,
    reports_route,
    evidence_route,
    tier1_route,
    tier2_route,
    sentinel_route,
    eol_certificate_route,
    monitor_route,
    resolver_route,
)
from boundstate_aegis import __version__

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    logger.info("AEGIS API starting up")
    yield
    logger.info("AEGIS API shutting down")


def create_app(
    title: str = "AEGIS API",
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        title: API title for documentation.
        cors_origins: List of allowed CORS origins. Defaults to localhost.

    Returns:
        Configured FastAPI application.
    """
    app = FastAPI(
        title=title,
        description=(
            "AEGIS - PFAS Risk Assessment API. "
            "Provides screening-level analysis of potential PFAS formation pathways "
            "from precursor materials under specified operating conditions."
        ),
        version=__version__,
        lifespan=lifespan,
    )

    # Configure CORS
    if cors_origins is None:
        cors_origins = [
            # Local development
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "http://localhost:8081",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8081",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
            # Production - boundstate.ai (HTTPS only)
            "https://boundstate.ai",
            "https://www.boundstate.ai",
            "https://aegis.boundstate.ai",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        # Allow Vercel previews and any boundstate.ai subdomain (HTTPS only)
        allow_origin_regex=r"https://.*\.(vercel\.app|boundstate\.ai)",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-AEGIS-API-Key", "Accept"],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Return a generic 500 while preserving server-side diagnostics."""
        logger.exception("Unhandled API error at %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    # Include routers
    app.include_router(
        assess_route.router,
        prefix="/api/pfas",
        tags=["PFAS Analysis"],
    )
    app.include_router(
        pathway_route.router,
        prefix="/api/pathways",
        tags=["Pathway Queries"],
    )
    app.include_router(
        regulation_route.router,
        prefix="/api/regulations",
        tags=["Regulatory Status"],
    )

    # V1 API routes for AEGIS UI
    app.include_router(
        fate_route.router,
        prefix="/api/v1/pfas",
        tags=["PFAS Fate Explorer"],
    )
    app.include_router(
        litigation_route.router,
        prefix="/api/v1/litigation",
        tags=["Litigation Risk"],
    )
    app.include_router(
        portfolio_route.router,
        prefix="/api/v1/portfolio",
        tags=["Portfolio Assessment"],
    )
    app.include_router(
        regulatory_v1_route.router,
        prefix="/api/v1/regulatory",
        tags=["Regulatory Compliance"],
    )
    app.include_router(
        reports_route.router,
        prefix="/api/v1/reports",
        tags=["Executive Reports"],
    )
    app.include_router(
        evidence_route.router,
        prefix="/api/v1/evidence",
        tags=["Evidence Chain"],
    )
    app.include_router(
        tier1_route.router,
        prefix="/api/v1/tier1",
        tags=["Tier 1 Structural Similarity"],
    )
    app.include_router(
        tier2_route.router,
        prefix="/api/v1/tier2",
        tags=["Tier 2 Substructure Rules"],
    )
    app.include_router(
        sentinel_route.router,
        prefix="/api/sentinel",
        tags=["SENTINEL Early Warning"],
    )
    app.include_router(
        eol_certificate_route.router,
        prefix="/api/v1/eol",
        tags=["EOL Proof Certificate"],
    )
    app.include_router(
        monitor_route.router,
        prefix="/api/v1/monitor",
        tags=["Regulatory Monitor Intelligence"],
    )
    app.include_router(
        resolver_route.router,
        prefix="/api/v1/resolver",
        tags=["Recursive Regulatory Resolver"],
    )

    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": __version__,
            "service": "aegis-api",
        }

    return app


# Default application instance
app = create_app()

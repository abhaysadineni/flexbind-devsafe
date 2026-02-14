"""FlexBind-DevSafe — Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router

app = FastAPI(
    title="FlexBind-DevSafe",
    description=(
        "Ensemble-aware binder design with developability gating. "
        "Upload a target and binder PDB to get robust, developable sequence designs."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(jobs_router)

"""
main.py
-------
FastAPI application factory.
Registers routers, middleware, and startup/shutdown lifecycle events.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import predict, risk, insights
from src.api.routes import auth
from src.api.dependencies import load_all_models
from src.utils.logger import get_logger
from src.db.database import engine, Base
from src.utils.config import CONFIG

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all models once at startup; release on shutdown."""
    logger.info("Starting up — loading models into cache...")
    load_all_models()
    logger.info("All models loaded.")
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created. API ready.")
    yield
    logger.info("Shutting down API.")


app = FastAPI(
    title="AI Disaster Intelligence API",
    description="Predict disaster types, estimate damage, and compute risk scores.",
    version=CONFIG["project"]["version"],
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Tighten to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(predict.router, prefix="/predict", tags=["Prediction"])
app.include_router(risk.router,    prefix="/risk",    tags=["Risk"])
app.include_router(insights.router,prefix="/insights",tags=["Insights"])
app.include_router(auth.router, prefix="/auth", tags=["Auth"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": CONFIG["project"]["version"]}
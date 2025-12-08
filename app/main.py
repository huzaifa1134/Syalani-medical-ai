from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.routes import webhook, health
from app.services.context_service import context_service
from app.services.rag_service import rag_service
from app.services.preferences_service import preferences_service
from app.utils.logger import setup_logging
import structlog

settings = get_settings()
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events"""

    logger.info("application_starting", env=settings.ENV, version=settings.API_VERSION)

    try:
        await context_service.connect()
        logger.info("context_redis_initialized")

        await preferences_service.connect()
        logger.info("preferences_redis_initialized")

        await rag_service.connect()
        logger.info("mongodb_initialized")

        logger.info("application_ready", features=['bilingual', 'voice_text_modes'])
    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise

    yield

    logger.info("application_shutting_down")

    try:
        await context_service.disconnect()
        await preferences_service.disconnect()
        rag_service.disconnect()
        logger.info("connection_closed")
    except Exception as e:
        logger.error("shutdown_error", error=str(e))

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    description="bilingual Whatsapp Voice/text AI Assistant - English and Urdu support",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(webhook.router, prefix=f"/api/{settings.API_VERSION}")
app.include_router(health.router, prefix=f"/api/{settings.API_VERSION}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.API_VERSION,
        "status": "running",
        "features": {
            "languages": ["Urdu", "English"],
            "modes": ["Voice", "Text"],
            "auto_detection": True
        },
        "docs": f"/docs" if settings.DEBUG else "disabled"
    }

@app.get("/api")
async def api_info():
    """API information""" 
    return {
        "name": settings.APP_NAME,
        "version": settings.API_VERSION,
        "endpoints": {
            "webhook": f"/api/{settings.API_VERSION}/webhook",
            "health": f"/api/{settings.API_VERSION}/health"
        },
        "supported_languages": ["ur", "en"],
        "interaction_modes": ["voice", "text"]
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
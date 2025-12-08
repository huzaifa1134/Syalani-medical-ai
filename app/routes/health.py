from logging import error
from fastapi import APIRouter
from app.models.schemas import HealthCheck
from app.config import get_settings
from datetime import datetime
from app.services.rag_service import rag_service
from app.services.context_service import context_service
import structlog

router = APIRouter(prefix="/health", tags=["health"])
logger = structlog.get_logger() 
settings = get_settings()

router.get("", response_model=HealthCheck)
async def health_check():
    """Health check endpoint to verify allservices are running"""
    services_status = {}

    try:
        if context_service.redis_client:
            await context_service.redis_client.ping()
            services_status["redis"] = "healthy"
        else:
            services_status["redis"] = "not_connected"
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        services_status["redis"] = "unhealthy"

    try:
        if rag_service.client:
            rag_service.client.admin.command("ping")
            services_status["mongodb"] = "healthy"
        else:
            services_status["mongodb"] = "not_connected"
    except Exception as e:
        logger.error("mongodb-health-check-failed", error=str(e))
        services_status["mongodb"] = "unhealthy"

    try:
        services_status["google_cloud_stt"] = "healthy"
        services_status["google_cloud_tts"] = "healthy"
    except Exception as e:
        logger.error("google_cloud_health_check_failed", error=str(e))
        services_status["google_cloud_stt"] = "unknown"
        services_status["google_cloud_tts"] = "unknown"

    try:
        services_status["gemini_llm"] = "healthy"
    except Exception as e:
        logger.error("gemini_health_check_failed", error=str(e))
        services_status["gemini_llm"] = "unknown"

    overall_status = "healthy" if all(status == "healthy" for status in services_status.values()) else "degraded"

    return HealthCheck(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services_status,
        version=settings.API_VERSION
    )

router.get("/ping")
async def ping():
    return {"status": "ok", "message": "pong"}
    
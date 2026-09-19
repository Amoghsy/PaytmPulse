from fastapi import APIRouter, Response, status
from app.database.connection import check_database_connection
from app.services.redis_service import check_redis_connection

router = APIRouter()


@router.get(
    "/",
    summary="Root Endpoint",
    description="Returns application metadata and running status."
)
def get_root():
    return {
        "application": "Paytm Pulse",
        "message": "Real-Time AI Business Partner for Every Merchant",
        "status": "running"
    }


@router.get(
    "/health",
    summary="General Health Check",
    description="Basic health check endpoint returning service status."
)
def get_health():
    return {
        "status": "healthy"
    }


@router.get(
    "/health/database",
    summary="Database Connection Health Check",
    description="Tests actual PostgreSQL database connection by executing a test query."
)
def get_health_database():
    is_healthy = check_database_connection()
    return {
        "service": "postgresql",
        "status": "healthy" if is_healthy else "unhealthy"
    }


@router.get(
    "/health/redis",
    summary="Redis Connection Health Check",
    description="Tests actual Redis connection by performing a PING operation."
)
def get_health_redis():
    is_healthy = check_redis_connection()
    return {
        "service": "redis",
        "status": "healthy" if is_healthy else "unhealthy"
    }


from app.services.n8n_service import check_n8n_connection


@router.get(
    "/health/n8n",
    summary="n8n Workflow Service Health Check",
    description="Checks reachability of the n8n workflow engine."
)
def get_health_n8n():
    is_healthy = check_n8n_connection()
    return {
        "service": "n8n",
        "status": "healthy" if is_healthy else "offline"
    }

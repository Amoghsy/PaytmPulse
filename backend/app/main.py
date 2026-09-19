import os
import time
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.api.health import router as health_router
from app.api.merchants import router as merchants_router
from app.api.products import router as products_router
from app.api.customers import router as customers_router
from app.api.transactions import router as transactions_router
from app.api.inventory import router as inventory_router

from app.database.connection import check_database_connection, engine, SessionLocal
from app.services.redis_service import check_redis_connection
from app.models import Base, Merchant
from app.database.seed import seed_data

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("paytm_pulse.main")


async def perform_startup_health_checks():
    if os.getenv("TESTING") == "1":
        return
    try:
        # Guarantee database schema tables exist
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema tables verified/created successfully.")
        
        # Auto-seed initial merchant catalog if fresh/empty database
        with SessionLocal() as session:
            count = session.query(Merchant).count()
            if count == 0:
                logger.info("Fresh database detected. Auto-seeding initial Paytm Pulse merchants and products...")
                seed_data(clear_existing=False)
                logger.info("Auto-seeding completed.")
    except Exception as e:
        logger.error(f"Error during schema setup / seeding: {str(e)}", exc_info=True)

    loop = asyncio.get_event_loop()
    db_status = await loop.run_in_executor(None, check_database_connection)
    logger.info(f"Initial Database Connection Status: {'Healthy' if db_status else 'Unhealthy'}")
    
    redis_status = await loop.run_in_executor(None, check_redis_connection)
    logger.info(f"Initial Redis Connection Status: {'Healthy' if redis_status else 'Unhealthy'}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Paytm Pulse Backend API...")
    asyncio.create_task(perform_startup_health_checks())
    yield
    logger.info("Shutting down Paytm Pulse Backend API...")

app = FastAPI(
    title="Paytm Pulse API",
    description="Real-Time AI Business Partner for Every Merchant - Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Robust CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"],
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(f"Request: {request.method} {request.url.path} - Status: {response.status_code} - Duration: {process_time:.2f}ms")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": str(exc),
                "path": request.url.path
            }
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

from app.api.events import router as events_router
from app.api.intelligence import router as intelligence_router
from app.api.agent import router as agent_router
from app.api.decisions import router as decisions_router
from app.communication.router import router as communication_router
from app.api.execution import router as execution_router
from app.api.outcomes import router as outcomes_router
from app.api.financial import router as financial_router
from app.api.memory import router as memory_router
from app.api.feedback import router as feedback_router
from app.api.system import router as system_router
from app.api.briefs import router as briefs_router
from app.api.voice import router as voice_router

# Include Routers
app.include_router(health_router)
app.include_router(system_router)
app.include_router(system_router, prefix="/api/v1")
app.include_router(merchants_router)
app.include_router(products_router)
app.include_router(customers_router)
app.include_router(transactions_router)
app.include_router(inventory_router)
app.include_router(events_router, prefix="/api/v1")
app.include_router(events_router)
app.include_router(intelligence_router, prefix="/api/v1")
app.include_router(intelligence_router)
app.include_router(agent_router, prefix="/api/v1")
app.include_router(agent_router)
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(decisions_router)
app.include_router(communication_router, prefix="/api/v1")
app.include_router(communication_router)
app.include_router(execution_router, prefix="/api/v1")
app.include_router(execution_router)
app.include_router(outcomes_router, prefix="/api/v1")
app.include_router(outcomes_router)
app.include_router(financial_router, prefix="/api/v1")
app.include_router(financial_router)
app.include_router(memory_router, prefix="/api/v1")
app.include_router(memory_router)
app.include_router(feedback_router, prefix="/api/v1")
app.include_router(feedback_router)
app.include_router(briefs_router, prefix="/api/v1")
app.include_router(briefs_router)
app.include_router(voice_router, prefix="/api/v1")
app.include_router(voice_router)



if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BACKEND_PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

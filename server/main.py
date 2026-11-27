"""
Main Application Entrypoint for Export Customs Documentation Compliance Checker (Backend).
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

from server.config.settings import get_settings
from server.logging.logger import get_logger
from server.middleware import setup_middlewares
from server.exceptions import register_exception_handlers
from server.routes.v1.router import api_v1_router

settings = get_settings()
logger = get_logger("server.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for startup and shutdown events.
    """
    logger.info(
        "Application starting up: project=%s, env=%s, port=%s",
        settings.PROJECT_NAME,
        settings.SERVER_ENV.value,
        settings.SERVER_PORT,
    )
    from server.rules.scheduler import get_rule_scheduler

    scheduler = get_rule_scheduler()
    scheduler.start()
    yield
    await scheduler.stop()
    logger.info("Application shutting down...")


def create_application() -> FastAPI:
    """
    FastAPI application factory.
    Configures middlewares, exception handlers, and versioned routes.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="Production API for Export Customs Documentation Compliance Checking",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 1. Setup Middlewares (Request ID, Logging, CORS)
    setup_middlewares(app)

    # 2. Register Global Exception Handlers
    register_exception_handlers(app)

    # 3. Mount Versioned API Routers
    app.include_router(api_v1_router)

    # 4. Root Welcome Route
    @app.get("/", tags=["Root"])
    async def root():
        return JSONResponse(
            content={
                "project": settings.PROJECT_NAME,
                "version": "1.0.0",
                "environment": settings.SERVER_ENV.value,
                "docs_url": "/docs",
                "api_v1_prefix": settings.API_V1_STR,
            }
        )

    return app


app = create_application()

if __name__ == "__main__":
    uvicorn.run(
        "server.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.SERVER_ENV.value == "development",
    )

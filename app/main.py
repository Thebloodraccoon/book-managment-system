import logging
from contextlib import asynccontextmanager

import uvicorn

from fastapi import FastAPI
from app.middleware.error_handler import setup_error_handlers
from app.ping.endpoints import router as ping_router
from app.auth.endpoints import router as auth_router
from app.users.endpoints import router as user_router
from app.books.endpoints import router as book_router
from app.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting up Book Managment System...")
    settings.Base.metadata.create_all(bind=settings.engine)
    yield
    logger.info("Shutting down Book Managment System...")

def setup_routers(app: FastAPI) -> None:
    """Setup API routes with proper versioning."""
    api_prefix = "/api"

    app.include_router(ping_router, prefix=f"{api_prefix}/ping", tags=["Health Check"])
    app.include_router(auth_router, prefix=f"{api_prefix}/auth", tags=["Auth"])
    app.include_router(user_router, prefix=f"{api_prefix}/users", tags=["Users"])
    app.include_router(book_router, prefix=f"{api_prefix}/books", tags=["Books"])


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Book Managment System",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    separate_input_output_schemas=True,
)

setup_error_handlers(app)
setup_routers(app)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=8000,
        reload=settings.STAGE == "local",
        workers=1 if settings.STAGE == "local" else 4,
        access_log=settings.STAGE != "prod",
        log_level="info" if settings.STAGE != "prod" else "warning",
    )

import logging
from fastapi import FastAPI

from app.core.config import settings
from app.api import chat,upload_api

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API to upload documents and generate pitch deck reports using RAG and LLM.",
)

logger.info("Starting FastAPI application...")

# Include routers
app.include_router(upload_api.router, prefix="/documents", tags=["Documents"])
logger.info("Included documents router.")

app.include_router(chat.router, prefix="/pitch", tags=["Pitch Deck"])
logger.info("Included pitch deck router.")


@app.get("/", tags=["Root"])
async def read_root():
    logger.info("Root endpoint '/' accessed.")
    return {"message": f"Welcome to the {settings.PROJECT_NAME}!"}

# Optional: Add startup/shutdown events if needed
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Application startup.")
#     # Initialize heavy resources here if needed (e.g., load models)
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("Application shutdown.")
    # Clean up resources here if needed

logger.info("FastAPI application configuration complete.")
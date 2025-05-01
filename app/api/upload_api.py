import shutil
import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from  app.schemas.file_schema import UploadResponse
from app.service.rag_service import RAGService 
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependency function to get RAGService instance
# This ensures a single instance is created and reused per request scope (or app scope if needed)
# If RAGService initialization is heavy, consider initializing it once at app startup
# and yielding it here. For now, this is simple.
def get_rag_service():
    # Consider error handling during RAGService init if it can fail
    return RAGService()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    rag_service: RAGService = Depends(get_rag_service) # Inject RAGService
):
    """
    Endpoint to upload a PDF, PPTX, or DOCX file.
    The file is saved locally and then processed by the RAGService.
    """
    # Ensure the data directory exists
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Define the path to save the file
    file_path = settings.DATA_DIR / file.filename
    logger.info(f"Received file: {file.filename}. Saving to: {file_path}")

    # Save the uploaded file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
    finally:
        # Ensure the file object is closed even if errors occur
        await file.close() # Use await for UploadFile's async close

    # Process the saved file using RAGService
    try:
        doc_id = rag_service.add_document(file_path)
        logger.info(f"Document {file.filename} processed successfully. Doc ID: {doc_id}")
        return UploadResponse(
            filename=file.filename,
            message="File uploaded and processed successfully.",
            doc_id=doc_id
        )
    except ValueError as ve: # Catch specific error for unsupported types
         logger.error(f"Unsupported file type for {file.filename}: {ve}", exc_info=True)
         # Optionally delete the saved file if processing fails
         # file_path.unlink(missing_ok=True)
         raise HTTPException(status_code=415, detail=str(ve)) # 415 Unsupported Media Type
    except Exception as e:
        logger.error(f"Failed to process document {file.filename} with RAGService: {e}", exc_info=True)
        # Optionally delete the saved file if processing fails
        # file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Could not process file: {e}")
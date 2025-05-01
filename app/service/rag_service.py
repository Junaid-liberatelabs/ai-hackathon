# app/services/rag_service.py
import logging
from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader # Add others as needed
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.vectorstores import VectorStoreRetriever # Import base class

from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        logger.info(f"Initializing RAGService with vector store path: {settings.VECTOR_STORE_DIR}")
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "default_key_if_not_set":
             logger.error("OPENAI_API_KEY not found.")
             raise ValueError("OPENAI_API_KEY is not configured.")

        self.embedding_function = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

        # Ensure the directory exists as a string path for Chroma
        persist_dir_str = str(settings.VECTOR_STORE_DIR.resolve())

        self.vector_store = Chroma(
            collection_name=settings.VECTOR_DB_COLLECTION_NAME,
            embedding_function=self.embedding_function,
            persist_directory=persist_dir_str
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        logger.info("RAGService initialized successfully with OpenAI Embeddings.")

    def add_document(self, file_path: Path) -> str:
        # ... (keep existing add_document logic) ...
        doc_id = file_path.name
        logger.info(f"Processing document: {doc_id} from path: {file_path}")
        try:
            if file_path.suffix.lower() == ".pdf":
                loader = PyPDFLoader(str(file_path))
            # TODO: Add loaders for .pptx, .docx etc.
            else:
                logger.error(f"Unsupported file type: {file_path.suffix}")
                raise ValueError(f"Unsupported file type: {file_path.suffix}")

            documents = loader.load()
            if not documents:
                logger.warning(f"No content loaded from document: {doc_id}")
                return doc_id

            logger.info(f"Loaded {len(documents)} pages/sections from {doc_id}")
            split_docs = self.text_splitter.split_documents(documents)
            logger.info(f"Split document {doc_id} into {len(split_docs)} chunks")

            if not split_docs:
                logger.warning(f"Document {doc_id} resulted in zero chunks after splitting.")
                return doc_id

            for chunk in split_docs:
                chunk.metadata = chunk.metadata or {}
                chunk.metadata["source"] = doc_id

            self.vector_store.add_documents(split_docs)
            # self.vector_store.persist() # Not needed for Chroma > 0.4

            logger.info(f"Successfully added document {doc_id} to vector store.")
            return doc_id
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}", exc_info=True)
            raise

    def get_retriever(self, search_kwargs={'k': 7}) -> VectorStoreRetriever:
        """Returns a retriever instance for the vector store."""
        logger.info(f"Creating retriever with search_kwargs: {search_kwargs}")
        return self.vector_store.as_retriever(search_kwargs=search_kwargs)

# --- ADD THIS FUNCTION ---
_rag_service_instance = None

def get_rag_service() -> RAGService:
    """Provides a singleton instance of the RAGService."""
    global _rag_service_instance
    if _rag_service_instance is None:
        logger.info("Creating new RAGService instance.")
        _rag_service_instance = RAGService()
    return _rag_service_instance
# --- END OF ADDED FUNCTION ---
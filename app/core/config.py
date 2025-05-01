import os
from pydantic_settings import BaseSettings
from pathlib import Path
from dotenv import load_dotenv
from functools import lru_cache

# Load environment variables from .env file
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Pitch Deck Generator API"
    VERSION: str = "0.1.0"

    # --- Paths ---
    # Use Path for better path handling
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent # Project root
    DATA_DIR: Path = BASE_DIR / "data"
    VECTOR_STORE_DIR: Path = BASE_DIR / "vector_store"

    # --- API Keys ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "default_key_if_not_set") # Get from env

    # --- RAG Settings ---
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2" # Good starting point
    VECTOR_DB_COLLECTION_NAME: str = "pitch_deck_documents_openai"
    
    LANGSMITH_TRACING : str
    LANGSMITH_ENDPOINT : str
    LANGSMITH_API_KEY : str
    LANGSMITH_PROJECT : str

    # --- LLM Settings ---
    LLM_MODEL_NAME: str = "gpt-4.1"

    class Config:
        case_sensitive = True
        # If using Pydantic v1: env_file = '.env', env_file_encoding = 'utf-8'
@lru_cache
def get_settings():
    
    load_dotenv(override=True)

    return Settings()

settings = Settings()

# Ensure necessary directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

print(f"Data directory: {settings.DATA_DIR}")
print(f"Vector store directory: {settings.VECTOR_STORE_DIR}")
# Simple check if API key is loaded (don't print the key itself in production logs)
print(f"OpenAI API Key Loaded: {'Yes' if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != 'default_key_if_not_set' else 'No'}")
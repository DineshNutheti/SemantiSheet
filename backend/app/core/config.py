# backend/app/core/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_PATH = BASE_DIR / "chroma_db"

# Create dirs if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database Settings
COLLECTION_NAME = "spreadsheet_concepts"

# Embedding Settings (LOCAL)
# 'BAAI/bge-m3' is SOTA for retrieval. 'all-MiniLM-L6-v2' is faster.
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5" 
EMBEDDING_BATCH_SIZE = 32  # Adjust based on VRAM/RAM

# LLM Settings (Remote for Synthesis)
GEMINI_API_KEY = os.getenv("LLM_API_KEY")
GENERATIVE_MODEL = "gemini-2.5-flash"
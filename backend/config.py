import os
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "storage", "uploads")
PARSED_DIR = os.path.join(os.path.dirname(__file__), "storage", "parsed")
GRAPHS_DIR = os.path.join(os.path.dirname(__file__), "storage", "graphs")
VECTORS_DIR = os.path.join(os.path.dirname(__file__), "storage", "vectors")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "storage", "reports")

CHUNK_SIZE = 600
CHUNK_OVERLAP = 80
RAG_TOP_K = 5
LLM_MAX_TOKENS = 8000

MERGE_THRESHOLD_HIGH = 0.90
MERGE_THRESHOLD_LOW = 0.82

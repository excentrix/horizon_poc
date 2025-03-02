# app/config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "student_mentors")

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# System Configuration
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
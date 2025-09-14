import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Databases
    MONGO_URI: str = os.getenv("MONGO_URI")
    DB_NAME: str = os.getenv("DB_NAME")
    NEO4J_URI: str = os.getenv("NEO4J_URI")
    NEO4J_USER: str = os.getenv("NEO4J_USER")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_TEMPERATURE: float = float(os.getenv("GEMINI_TEMPERATURE", 0.7))
    GEMINI_TOP_P: float = float(os.getenv("GEMINI_TOP_P", 0.9))
    GEMINI_TOP_K: int = int(os.getenv("GEMINI_TOP_K", 40))
    GEMINI_THINKING_BUDGET: int = int(os.getenv("GEMINI_THINKING_BUDGET", -1))
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY")

    AUDIO_FILES_DIR: str = "audio_records"

settings = Settings()
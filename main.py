from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import auth_router, chat_router, user_router, hospitals_router
from database import db  # Import the db instance
from config import settings
from neo4j_driver import close_neo4j_driver

# --- Lifespan Manager ---
# This is the modern way to handle startup and shutdown events in FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    db.connect(settings.MONGO_URI, settings.DB_NAME)
    yield
    # Code to run on shutdown
    db.close()
    close_neo4j_driver()

app = FastAPI(
    title="SageAI Medical Advisor API",
    description="A modular API for a comprehensive medical assistant.",
    version="1.0.0",
    lifespan=lifespan  # <-- ATTACH THE LIFESPAN MANAGER
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Routers ---
app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(user_router.router)
app.include_router(hospitals_router.router)

# --- Root Endpoint ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the SageAI Medical Advisor API"}

@app.get("/health")
def health_check():
    try:
        # Check DB connection
        db.client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
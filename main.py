
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- VERIFY THIS IMPORT LINE ---
from api import auth_router, chat_router, user_router, hospitals_router, appointments_router
from database import db
from config import settings
from neo4j_driver import close_neo4j_driver

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.connect(settings.MONGO_URI, settings.DB_NAME)
    yield
    db.close()
    close_neo4j_driver()

app = FastAPI(
    title="SageAI Medical Advisor API",
    description="A modular API for a comprehensive medical assistant.",
    version="1.0.0",
    lifespan=lifespan
)

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

# --- VERIFY THIS LINE IS PRESENT ---
app.include_router(appointments_router.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the SageAI Medical Advisor API"}

@app.get("/health")
def health_check():
    try:
        db.client.admin.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

# Import routers
from api import auth_router, chat_router, user_router, hospitals_router, appointments_router
from database import db
from config import settings
from neo4j_driver import close_neo4j_driver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('api_logs.log')
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SageAI Medical Advisor API...")
    try:
        db.connect(settings.MONGO_URI, settings.DB_NAME)
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    yield
    logger.info("Shutting down SageAI Medical Advisor API...")
    db.close()
    close_neo4j_driver()

app = FastAPI(
    title="SageAI Medical Advisor API",
    description="A modular API for a comprehensive medical assistant.",
    version="1.0.0",
    lifespan=lifespan
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log the request
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log the response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
    
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handler for better error logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception on {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# --- API Routers ---
logger.info("Including API routers...")
app.include_router(auth_router.router)
app.include_router(chat_router.router)
app.include_router(user_router.router)
app.include_router(hospitals_router.router)
app.include_router(appointments_router.router)
logger.info("All routers included successfully")

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
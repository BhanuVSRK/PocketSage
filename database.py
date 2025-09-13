import logging
from pymongo import MongoClient
from config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.client: MongoClient = None
        self.db = None
        self.user_collection = None
        self.chat_collection = None

    def connect(self, uri: str, db_name: str):
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ismaster')
            self.db = self.client[db_name]
            self.user_collection = self.db.users
            self.chat_collection = self.db.chats
            logger.info(f"Successfully connected to MongoDB database: '{db_name}'")
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to connect to MongoDB at {uri}. Error: {e}")
            raise

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")

# Create a single, global instance that we will connect to on startup
db = Database()

def get_db_collections():
    """FastAPI dependency to get database collections."""
    # --- FIX: Explicitly check for None instead of using 'not' ---
    if db.user_collection is None or db.chat_collection is None:
        raise RuntimeError("Database is not initialized. Check MongoDB connection.")
    return db.user_collection, db.chat_collection
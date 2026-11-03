import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FoodWastePredictor")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/food_waste_db")
DB_NAME = os.getenv("DB_NAME", "food_waste_db")
PYTHON_PORT = int(os.getenv("PYTHON_PORT", 5000))
NODE_PORT = int(os.getenv("NODE_PORT", 3000))
WASTE_THRESHOLD_PERCENT = float(os.getenv("WASTE_THRESHOLD_PERCENT", 15.0))
MIN_RETRAIN_RECORDS = int(os.getenv("MIN_RETRAIN_RECORDS", 50))

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
MOCK_DATA_FILE = DATA_DIR / "persistent_meals_backup.json"

db = None
db_client = None
db_status = {
    "connected": False,
    "mode": "unknown",
    "details": "Initializing..."
}

def get_database():
    """
    Connect to MongoDB via PyMongo.
    If live MongoDB connection is unavailable, fallback to persistent mongomock
    so that application can run standalone while notifying the user.
    """
    global db, db_client, db_status
    if db is not None:
        return db

    # Mask password for secure logging in console
    import re
    masked_uri = re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', MONGODB_URI)

    try:
        logger.info(f"Connecting to MongoDB at: {masked_uri} (timeout 5s)...")
        client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')
        db = client[DB_NAME]
        db_client = client
        db_status = {
            "connected": True,
            "mode": "mongodb_live",
            "details": f"Connected to live MongoDB ({DB_NAME})"
        }
        logger.info(f"Successfully connected to live MongoDB: {DB_NAME}")
        return db
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as e:
        logger.warning(f"Could not connect to live MongoDB: {e}")
        logger.info("Falling back to persistent PyMongo-compatible mock database store...")
        import mongomock
        mock_client = mongomock.MongoClient()
        mock_db = mock_client[DB_NAME]

        # Load persisted records if available
        if MOCK_DATA_FILE.exists():
            try:
                with open(MOCK_DATA_FILE, "r", encoding="utf-8") as f:
                    cached_records = json.load(f)
                    if cached_records:
                        mock_db.meals.insert_many(cached_records)
                        logger.info(f"Loaded {len(cached_records)} cached meals into mock store.")
            except Exception as load_err:
                logger.error(f"Failed to load cached records: {load_err}")

        db = mock_db
        db_client = mock_client
        db_status = {
            "connected": True,
            "mode": "mongodb_fallback",
            "details": "MongoDB offline: Using persistent PyMongo-compatible fallback. Configure MONGODB_URI in .env for live Atlas or local server."
        }
        return db

def get_db_status():
    """Return live database status dictionary."""
    global db, db_status
    if db is None:
        get_database()
    return db_status

def sync_mock_storage():
    """Persist mock database records to local disk if running in fallback mode."""
    global db, db_status
    if db_status.get("mode") == "mongodb_fallback" and db is not None:
        try:
            records = list(db.meals.find({}, {"_id": 0}))
            with open(MOCK_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error syncing mock storage: {e}")

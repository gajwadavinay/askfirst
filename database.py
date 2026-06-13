import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

# Initialize MongoClient. check_same_thread is not needed for PyMongo as it is thread-safe.
client = MongoClient(MONGO_URI)
db = client["askfirst"]

def init_db():
    # Ping the database to verify active connection on startup
    try:
        client.admin.command("ping")
    except Exception as e:
        raise ConnectionError(f"Failed to connect to MongoDB: {e}")

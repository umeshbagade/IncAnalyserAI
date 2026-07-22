"""
MongoDB connection manager using Motor (async driver).
Loads credentials from .env file.
"""

import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "incanalyserai")
MONGODB_COLLECTION_INCIDENTS = os.getenv("MONGODB_COLLECTION_INCIDENTS", "incidents")

client: Optional[AsyncIOMotorClient] = None
db: Optional[AsyncIOMotorDatabase] = None
incidents_collection: Optional[AsyncIOMotorCollection] = None


async def connect_to_mongo():
    """Initialize MongoDB connection."""
    global client, db, incidents_collection

    # Add TLS params for MongoDB Atlas
    url = MONGODB_URL
    if "?" not in url:
        url += "?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"
    else:
        url += "&tlsAllowInvalidCertificates=true"

    client = AsyncIOMotorClient(
        url,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=20000,
    )
    db = client[MONGODB_DB_NAME]
    incidents_collection = db[MONGODB_COLLECTION_INCIDENTS]

    # Verify connection by pinging
    await client.admin.command('ping')
    print(f"✅ Connected to MongoDB: {MONGODB_DB_NAME}.{MONGODB_COLLECTION_INCIDENTS}")

    # Create index on incident id for fast lookups
    await incidents_collection.create_index("id", unique=True)
    # Create index on status for filtering
    await incidents_collection.create_index("status")

    print(f"📊 Indexes created on '{MONGODB_COLLECTION_INCIDENTS}' collection")
    return client, db, incidents_collection


async def close_mongo_connection():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("🔒 MongoDB connection closed")


async def get_incidents_collection() -> AsyncIOMotorCollection:
    """Get the incidents collection."""
    if incidents_collection is None:
        await connect_to_mongo()
    return incidents_collection


def get_db() -> Optional[AsyncIOMotorDatabase]:
    """Get the database instance."""
    return db


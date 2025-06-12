"""
MongoDB Atlas client for Agent Zero
Handles connection, authentication, and basic operations
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from python.helpers.dotenv import get_dotenv_value
from python.helpers.print_style import PrintStyle


class MongoDBClient:
    """MongoDB Atlas client with async support"""
    
    def __init__(self):
        self._async_client: Optional[AsyncIOMotorClient] = None
        self._sync_client: Optional[MongoClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None
        self._connected = False
        
        # Configuration from environment
        self.uri = get_dotenv_value("MONGODB_URI") or get_dotenv_value("MONGODB_ATLAS_URI")
        self.database_name = get_dotenv_value("MONGODB_DATABASE") or "agent_zero"
        
        if not self.uri:
            PrintStyle.warning("MongoDB URI not found in environment variables")
            PrintStyle.hint("Please set MONGODB_URI or MONGODB_ATLAS_URI in your .env file")
    
    async def connect(self) -> bool:
        """Connect to MongoDB Atlas"""
        if self._connected:
            return True
            
        if not self.uri:
            PrintStyle.error("Cannot connect to MongoDB: No URI provided")
            return False
            
        try:
            PrintStyle.standard("Connecting to MongoDB Atlas...")
            
            # Create async client
            self._async_client = AsyncIOMotorClient(
                self.uri,
                serverSelectionTimeoutMS=5000,  # 5 second timeout
                connectTimeoutMS=10000,  # 10 second timeout
                maxPoolSize=10
            )
            
            # Test connection
            await self._async_client.admin.command('ping')
            
            # Get database
            self._database = self._async_client[self.database_name]
            
            self._connected = True
            PrintStyle.success(f"Connected to MongoDB Atlas database: {self.database_name}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            PrintStyle.error(f"Failed to connect to MongoDB Atlas: {str(e)}")
            return False
        except Exception as e:
            PrintStyle.error(f"Unexpected error connecting to MongoDB: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self._async_client:
            self._async_client.close()
            self._async_client = None
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
        self._database = None
        self._connected = False
        PrintStyle.standard("Disconnected from MongoDB Atlas")
    
    def get_database(self) -> Optional[AsyncIOMotorDatabase]:
        """Get the database instance"""
        return self._database
    
    def get_collection(self, collection_name: str) -> Optional[AsyncIOMotorCollection]:
        """Get a collection from the database"""
        if self._database is None:
            return None
        return self._database[collection_name]
    
    async def ensure_connected(self) -> bool:
        """Ensure connection is established"""
        if not self._connected:
            return await self.connect()
        return True
    
    async def test_connection(self) -> bool:
        """Test if connection is working"""
        try:
            if not await self.ensure_connected():
                return False
            await self._async_client.admin.command('ping')
            return True
        except Exception as e:
            PrintStyle.error(f"MongoDB connection test failed: {str(e)}")
            return False
    
    async def create_indexes(self, collection_name: str, indexes: List[Dict[str, Any]]):
        """Create indexes for a collection"""
        try:
            if not await self.ensure_connected():
                return False
                
            collection = self.get_collection(collection_name)
            if collection is None:
                return False
                
            for index_spec in indexes:
                await collection.create_index(index_spec)
                
            PrintStyle.success(f"Created indexes for collection: {collection_name}")
            return True
            
        except Exception as e:
            PrintStyle.error(f"Failed to create indexes: {str(e)}")
            return False
    
    async def get_collection_stats(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a collection"""
        try:
            if not await self.ensure_connected():
                return None
                
            db = self.get_database()
            if db is None:
                return None
                
            stats = await db.command("collStats", collection_name)
            return stats
            
        except Exception as e:
            PrintStyle.warning(f"Could not get stats for collection {collection_name}: {str(e)}")
            return None


# Global MongoDB client instance
_mongodb_client: Optional[MongoDBClient] = None


async def get_mongodb_client() -> MongoDBClient:
    """Get or create the global MongoDB client"""
    global _mongodb_client
    
    if _mongodb_client is None:
        _mongodb_client = MongoDBClient()
        await _mongodb_client.connect()
    
    return _mongodb_client


async def close_mongodb_client():
    """Close the global MongoDB client"""
    global _mongodb_client
    
    if _mongodb_client:
        await _mongodb_client.disconnect()
        _mongodb_client = None

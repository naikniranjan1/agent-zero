#!/usr/bin/env python3
"""
Test MongoDB Atlas connection
"""

import sys
import os
from pymongo import MongoClient

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.helpers.dotenv import get_dotenv_value


def test_connection():
    """Test MongoDB connection"""
    print("=== MongoDB Atlas Connection Test ===")
    
    # Get connection string
    mongodb_uri = get_dotenv_value("MONGODB_URI")
    
    if not mongodb_uri:
        print("❌ No MongoDB URI found")
        return False
    
    print(f"Connecting to MongoDB Atlas...")
    
    try:
        # Create client
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ Connection successful!")
        
        # Test database
        db = client["agent_zero"]
        collections = db.list_collection_names()
        print(f"✅ Database accessible. Collections: {collections}")
        
        # Test write
        test_collection = db["test"]
        result = test_collection.insert_one({"test": "success"})
        print(f"✅ Write test successful: {result.inserted_id}")
        
        # Cleanup
        test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Cleanup successful")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_connection()
    if success:
        print("\n🎉 MongoDB Atlas setup complete!")
        print("\nNext steps:")
        print("1. Create vector search index in MongoDB Atlas UI")
        print("2. Set VECTOR_STORE_PROVIDER=mongodb in .env")
        print("3. Test with Agent Zero")
    else:
        print("\n❌ Setup failed")

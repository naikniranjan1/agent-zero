#!/usr/bin/env python3
"""
Direct MongoDB Atlas connection test
"""

import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

def test_mongodb():
    """Test MongoDB connection"""
    print("=== MongoDB Atlas Connection Test ===")
    
    # Get connection string
    mongodb_uri = os.getenv("MONGODB_URI")
    
    if not mongodb_uri:
        print("❌ No MongoDB URI found in environment")
        return False
    
    print("✅ MongoDB URI found")
    print(f"Connecting to: {mongodb_uri.split('@')[1].split('?')[0]}")
    
    try:
        # Create client
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=10000)
        
        # Test connection
        print("Testing connection...")
        client.admin.command('ping')
        print("✅ MongoDB Atlas connection successful!")
        
        # Test database access
        db_name = "agent_zero"
        db = client[db_name]
        
        print(f"Testing database access: {db_name}")
        collections = db.list_collection_names()
        print(f"✅ Database accessible. Existing collections: {collections if collections else 'None'}")
        
        # Test write operation
        print("Testing write operation...")
        test_collection = db["test_connection"]
        test_doc = {"test": "Phase 1 & 2 setup", "status": "success"}
        result = test_collection.insert_one(test_doc)
        print(f"✅ Write successful - Document ID: {result.inserted_id}")
        
        # Test read operation
        print("Testing read operation...")
        found_doc = test_collection.find_one({"_id": result.inserted_id})
        print(f"✅ Read successful - Document: {found_doc}")
        
        # Cleanup
        test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Cleanup successful")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_mongodb()
    
    if success:
        print("\n🎉 Phase 1 & 2 MongoDB Setup Complete!")
        print("\n=== Next Steps ===")
        print("1. Create Vector Search Index in MongoDB Atlas:")
        print("   - Go to MongoDB Atlas Dashboard")
        print("   - Database → Search → Create Search Index")
        print("   - Select 'Atlas Vector Search'")
        print("   - Database: agent_zero")
        print("   - Collection: user_memory")
        print("   - Index name: vector_search_index")
        print("\n2. Vector Index Configuration (JSON):")
        print("""{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "user_id"
    },
    {
      "type": "filter",
      "path": "metadata.timestamp"
    }
  ]
}""")
        print("\n3. Enable MongoDB in Agent Zero:")
        print("   - Set VECTOR_STORE_PROVIDER=mongodb in .env")
        print("   - Restart Agent Zero")
        
    else:
        print("\n❌ MongoDB setup failed")
        print("Please check your connection and try again")

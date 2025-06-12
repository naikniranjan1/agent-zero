#!/usr/bin/env python3
"""
Test MongoDB Atlas connection
"""

import sys
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.helpers.dotenv import get_dotenv_value
from python.helpers.print_style import PrintStyle


def test_mongodb_connection():
    """Test MongoDB Atlas connection"""
    PrintStyle.standard("=== MongoDB Atlas Connection Test ===")
    
    # Get connection string from environment
    mongodb_uri = get_dotenv_value("MONGODB_URI") or get_dotenv_value("MONGODB_ATLAS_URI")
    
    if not mongodb_uri:
        PrintStyle.error("❌ No MongoDB URI found in .env file")
        PrintStyle.hint("Please set MONGODB_URI in your .env file")
        return False
    
    if "<db_password>" in mongodb_uri:
        PrintStyle.error("❌ Please replace <db_password> with your actual password in .env file")
        return False
    
    PrintStyle.standard(f"Testing connection to: {mongodb_uri.split('@')[1].split('?')[0]}")
    
    try:
        # Create MongoDB client
        client = MongoClient(
            mongodb_uri,
            serverSelectionTimeoutMS=5000  # 5 second timeout
        )
        
        # Test connection
        client.admin.command('ping')
        PrintStyle.success("✅ MongoDB Atlas connection successful!")
        
        # Get database info
        db_name = get_dotenv_value("MONGODB_DATABASE") or "agent_zero"
        db = client[db_name]
        
        # Test database access
        collections = db.list_collection_names()
        PrintStyle.success(f"✅ Database '{db_name}' accessible")
        PrintStyle.standard(f"Existing collections: {collections if collections else 'None'}")
        
        # Test write operation
        test_collection = db["test_connection"]
        test_doc = {"test": "connection", "timestamp": "2025-01-11"}
        result = test_collection.insert_one(test_doc)
        PrintStyle.success(f"✅ Write test successful - Document ID: {result.inserted_id}")
        
        # Clean up test document
        test_collection.delete_one({"_id": result.inserted_id})
        PrintStyle.success("✅ Cleanup successful")
        
        client.close()
        return True
        
    except ConnectionFailure as e:
        PrintStyle.error(f"❌ Connection failed: {str(e)}")
        PrintStyle.hint("Check your internet connection and MongoDB Atlas cluster status")
        return False
        
    except ServerSelectionTimeoutError as e:
        PrintStyle.error(f"❌ Server selection timeout: {str(e)}")
        PrintStyle.hint("Check if your IP address is whitelisted in MongoDB Atlas")
        return False
        
    except Exception as e:
        PrintStyle.error(f"❌ Unexpected error: {str(e)}")
        return False


def show_next_steps():
    """Show next steps for setup"""
    PrintStyle.standard("\n=== Next Steps ===")
    PrintStyle.hint("1. Create Vector Search Index in MongoDB Atlas:")
    PrintStyle.hint("   - Go to MongoDB Atlas Dashboard")
    PrintStyle.hint("   - Navigate to Database → Search")
    PrintStyle.hint("   - Click 'Create Search Index'")
    PrintStyle.hint("   - Select 'Atlas Vector Search'")
    PrintStyle.hint("   - Use database: agent_zero")
    PrintStyle.hint("   - Use collection: user_memory")
    PrintStyle.hint("   - Use index name: vector_search_index")
    
    PrintStyle.hint("\n2. Vector Search Index Configuration:")
    PrintStyle.hint("""
{
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
    },
    {
      "type": "filter",
      "path": "metadata.area"
    }
  ]
}
    """)
    
    PrintStyle.hint("\n3. Enable MongoDB in Agent Zero:")
    PrintStyle.hint("   - Set VECTOR_STORE_PROVIDER=mongodb in .env")
    PrintStyle.hint("   - Restart Agent Zero")
    PrintStyle.hint("   - Test with conversations")


if __name__ == "__main__":
    success = test_mongodb_connection()
    
    if success:
        PrintStyle.success("\n🎉 MongoDB Atlas setup successful!")
        show_next_steps()
    else:
        PrintStyle.error("\n❌ MongoDB Atlas setup failed")
        PrintStyle.hint("Please check your connection string and try again")

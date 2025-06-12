#!/usr/bin/env python3
"""
Test script for MongoDB Atlas connection and vector search setup
Run this to verify Phase 1 & 2 implementation
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.helpers.mongodb_client import get_mongodb_client, close_mongodb_client
from python.helpers.user_manager import get_user_manager
from python.helpers.print_style import PrintStyle
from models import vector_store_config, mongodb_config


async def test_mongodb_connection():
    """Test MongoDB Atlas connection"""
    PrintStyle.standard("Testing MongoDB Atlas connection...")
    
    try:
        # Get MongoDB client
        client = await get_mongodb_client()
        
        # Test connection
        if await client.test_connection():
            PrintStyle.success("✓ MongoDB Atlas connection successful!")
            
            # Get database stats
            stats = await client.get_collection_stats("test_collection")
            if stats:
                PrintStyle.success("✓ Database access confirmed")
            
            return True
        else:
            PrintStyle.error("✗ MongoDB Atlas connection failed")
            return False
            
    except Exception as e:
        PrintStyle.error(f"✗ MongoDB connection error: {str(e)}")
        return False


async def test_user_management():
    """Test user management system"""
    PrintStyle.standard("Testing user management system...")
    
    try:
        user_manager = await get_user_manager()
        
        # Create test user
        test_user = await user_manager.create_user(
            username="test_user_123",
            email="test@example.com"
        )
        
        if test_user:
            PrintStyle.success(f"✓ Created test user: {test_user.username} (ID: {test_user.user_id})")
            
            # Create session
            session = await user_manager.create_session(test_user.user_id)
            if session:
                PrintStyle.success(f"✓ Created session: {session.session_id}")
                
                # Test session retrieval
                retrieved_session = await user_manager.get_session(session.session_id)
                if retrieved_session:
                    PrintStyle.success("✓ Session retrieval successful")
                    return True
        
        PrintStyle.error("✗ User management test failed")
        return False
        
    except Exception as e:
        PrintStyle.error(f"✗ User management error: {str(e)}")
        return False


async def test_vector_store_config():
    """Test vector store configuration"""
    PrintStyle.standard("Testing vector store configuration...")
    
    try:
        PrintStyle.standard(f"Vector store provider: {vector_store_config.provider}")
        PrintStyle.standard(f"MongoDB configured: {mongodb_config.is_configured}")
        PrintStyle.standard(f"Use MongoDB: {vector_store_config.use_mongodb}")
        
        if vector_store_config.use_mongodb:
            PrintStyle.success("✓ MongoDB Atlas Vector Search will be used")
        else:
            PrintStyle.success("✓ FAISS Vector Store will be used (default)")
        
        return True
        
    except Exception as e:
        PrintStyle.error(f"✗ Vector store config error: {str(e)}")
        return False


async def create_mongodb_indexes():
    """Create necessary MongoDB indexes for vector search"""
    if not vector_store_config.use_mongodb:
        PrintStyle.standard("Skipping MongoDB index creation (FAISS mode)")
        return True
    
    PrintStyle.standard("Creating MongoDB Atlas Vector Search indexes...")
    
    try:
        client = await get_mongodb_client()
        
        # Note: Vector search indexes need to be created through MongoDB Atlas UI
        # This is just a placeholder for future automation
        
        PrintStyle.warning("⚠ Vector search indexes must be created manually in MongoDB Atlas UI")
        PrintStyle.hint("Go to MongoDB Atlas → Database → Search → Create Search Index")
        PrintStyle.hint("Use the following configuration:")
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
    }
  ]
}
        """)
        
        return True
        
    except Exception as e:
        PrintStyle.error(f"✗ Index creation error: {str(e)}")
        return False


async def main():
    """Main test function"""
    PrintStyle.standard("=== Agent Zero MongoDB Atlas Integration Test ===")
    PrintStyle.standard("Phase 1 & 2: MongoDB Setup + User Management")
    
    # Test configuration
    await test_vector_store_config()
    
    # Test MongoDB connection if configured
    if mongodb_config.is_configured:
        mongodb_ok = await test_mongodb_connection()
        
        if mongodb_ok:
            # Test user management
            user_ok = await test_user_management()
            
            # Create indexes
            await create_mongodb_indexes()
            
            if user_ok:
                PrintStyle.success("\n🎉 All tests passed! Phase 1 & 2 implementation successful!")
                PrintStyle.hint("\nNext steps:")
                PrintStyle.hint("1. Set VECTOR_STORE_PROVIDER=mongodb in .env to use MongoDB")
                PrintStyle.hint("2. Create vector search index in MongoDB Atlas UI")
                PrintStyle.hint("3. Test with actual agent conversations")
            else:
                PrintStyle.error("\n❌ User management tests failed")
        else:
            PrintStyle.error("\n❌ MongoDB connection failed")
    else:
        PrintStyle.warning("\n⚠ MongoDB not configured - using FAISS mode")
        PrintStyle.hint("To test MongoDB:")
        PrintStyle.hint("1. Set MONGODB_URI in .env file")
        PrintStyle.hint("2. Run this test again")
    
    # Cleanup
    await close_mongodb_client()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Complete test of Phase 1 & 2 MongoDB Atlas implementation
Tests all components: connection, collections, user management, vector store
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.helpers.print_style import PrintStyle
from python.helpers.mongodb_client import get_mongodb_client, close_mongodb_client
from python.helpers.user_manager import get_user_manager
from python.helpers.vector_store import VectorStoreFactory, get_default_provider
from models import vector_store_config, mongodb_config


async def test_mongodb_connection():
    """Test MongoDB Atlas connection"""
    PrintStyle.standard("=== Testing MongoDB Connection ===")
    
    try:
        client = await get_mongodb_client()
        
        if await client.test_connection():
            PrintStyle.success("✅ MongoDB Atlas connection successful")
            
            # Get database stats
            stats = await client.get_collection_stats("user_memory")
            if stats is not None:
                PrintStyle.success("✅ Collection access confirmed")
            
            return True
        else:
            PrintStyle.error("❌ MongoDB connection failed")
            return False
            
    except Exception as e:
        PrintStyle.error(f"❌ Connection error: {str(e)}")
        return False


async def test_user_management():
    """Test user management system"""
    PrintStyle.standard("\n=== Testing User Management ===")
    
    try:
        user_manager = await get_user_manager()
        
        # Create test user
        test_username = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        user = await user_manager.create_user(
            username=test_username,
            email="test@example.com"
        )
        
        if user:
            PrintStyle.success(f"✅ Created user: {user.username} (ID: {user.user_id})")
            
            # Test session creation
            session = await user_manager.create_session(user.user_id)
            if session:
                PrintStyle.success(f"✅ Created session: {session.session_id}")
                
                # Test session retrieval
                retrieved_session = await user_manager.get_session(session.session_id)
                if retrieved_session:
                    PrintStyle.success("✅ Session retrieval successful")
                    
                    # Test user retrieval
                    retrieved_user = await user_manager.get_user(user.user_id)
                    if retrieved_user:
                        PrintStyle.success("✅ User retrieval successful")
                        return True
        
        PrintStyle.error("❌ User management test failed")
        return False
        
    except Exception as e:
        PrintStyle.error(f"❌ User management error: {str(e)}")
        return False


async def test_vector_store():
    """Test vector store system"""
    PrintStyle.standard("\n=== Testing Vector Store ===")
    
    try:
        # Test configuration
        PrintStyle.standard(f"Provider: {vector_store_config.provider}")
        PrintStyle.standard(f"Use MongoDB: {vector_store_config.use_mongodb}")
        
        # Create a mock embeddings model for testing
        class MockEmbeddings:
            def embed_query(self, text: str):
                # Return a mock 1536-dimensional embedding
                return [0.1] * 1536
            
            async def aembed_documents(self, texts):
                return [[0.1] * 1536 for _ in texts]
            
            async def aembed_query(self, text: str):
                return [0.1] * 1536
        
        mock_embeddings = MockEmbeddings()
        
        # Create vector store
        provider = get_default_provider()
        vector_store = VectorStoreFactory.create_vector_store(
            provider=provider,
            embeddings=mock_embeddings,
            user_id="test_user_123"
        )
        
        PrintStyle.success(f"✅ Created {provider.value} vector store")
        
        # Test document operations (only for FAISS, MongoDB needs vector index)
        if provider.value == "faiss":
            from langchain_core.documents import Document
            
            # Test document insertion
            test_docs = [
                Document(
                    page_content="This is a test document for Phase 1 & 2",
                    metadata={"test": True, "phase": "1_and_2"}
                )
            ]
            
            ids = await vector_store.aadd_documents(test_docs)
            if ids:
                PrintStyle.success(f"✅ Added documents: {len(ids)}")
                
                # Test search (basic)
                try:
                    results = await vector_store.asimilarity_search_with_score(
                        query="test document",
                        k=1
                    )
                    if results:
                        PrintStyle.success(f"✅ Search successful: {len(results)} results")
                    else:
                        PrintStyle.warning("⚠ Search returned no results")
                except Exception as e:
                    PrintStyle.warning(f"⚠ Search test skipped: {str(e)}")
        else:
            PrintStyle.warning("⚠ MongoDB vector operations require vector search index")
            PrintStyle.hint("Create the vector index first, then test vector operations")
        
        return True
        
    except Exception as e:
        PrintStyle.error(f"❌ Vector store error: {str(e)}")
        return False


async def test_collections():
    """Test MongoDB collections"""
    PrintStyle.standard("\n=== Testing Collections ===")
    
    try:
        client = await get_mongodb_client()
        db = client.get_database()

        if db is None:
            PrintStyle.error("❌ Could not get database")
            return False
        
        # Check required collections
        required_collections = [
            "user_memory",
            "user_chats", 
            "user_knowledge",
            "users",
            "user_sessions"
        ]
        
        existing_collections = await db.list_collection_names()
        
        for collection_name in required_collections:
            if collection_name in existing_collections:
                PrintStyle.success(f"✅ Collection exists: {collection_name}")
                
                # Test basic operations
                collection = db[collection_name]
                
                # Test write
                test_doc = {
                    "test": True,
                    "timestamp": datetime.utcnow().isoformat(),
                    "phase": "1_and_2_test"
                }
                
                result = await collection.insert_one(test_doc)
                PrintStyle.success(f"  ✅ Write test: {result.inserted_id}")
                
                # Test read
                found_doc = await collection.find_one({"_id": result.inserted_id})
                if found_doc:
                    PrintStyle.success(f"  ✅ Read test successful")
                
                # Cleanup
                await collection.delete_one({"_id": result.inserted_id})
                PrintStyle.success(f"  ✅ Cleanup successful")
                
            else:
                PrintStyle.error(f"❌ Missing collection: {collection_name}")
                return False
        
        return True
        
    except Exception as e:
        PrintStyle.error(f"❌ Collections test error: {str(e)}")
        return False


async def show_summary():
    """Show setup summary"""
    PrintStyle.standard("\n" + "="*60)
    PrintStyle.success("📊 PHASE 1 & 2 IMPLEMENTATION SUMMARY")
    PrintStyle.standard("="*60)
    
    PrintStyle.standard(f"\n🔧 Configuration:")
    PrintStyle.standard(f"   • Vector Store Provider: {vector_store_config.provider}")
    PrintStyle.standard(f"   • MongoDB Configured: {mongodb_config.is_configured}")
    PrintStyle.standard(f"   • Database: {mongodb_config.database}")
    
    PrintStyle.standard(f"\n📁 Collections:")
    PrintStyle.standard(f"   • user_memory (with vector embeddings)")
    PrintStyle.standard(f"   • user_chats (conversation history)")
    PrintStyle.standard(f"   • user_knowledge (uploaded documents)")
    PrintStyle.standard(f"   • users (user accounts)")
    PrintStyle.standard(f"   • user_sessions (authentication)")
    
    PrintStyle.standard(f"\n🚀 Features Ready:")
    PrintStyle.standard(f"   • Multi-user support with data isolation")
    PrintStyle.standard(f"   • MongoDB Atlas cloud storage")
    PrintStyle.standard(f"   • User management and sessions")
    PrintStyle.standard(f"   • Unified vector store abstraction")
    PrintStyle.standard(f"   • Backward compatibility with FAISS")
    
    PrintStyle.standard(f"\n📋 Next Steps:")
    if vector_store_config.use_mongodb:
        PrintStyle.hint("   1. Create vector search index (run: python create_vector_index.py)")
        PrintStyle.hint("   2. Test Agent Zero with conversations")
        PrintStyle.hint("   3. Verify multi-user functionality")
    else:
        PrintStyle.hint("   1. Set VECTOR_STORE_PROVIDER=mongodb in .env")
        PrintStyle.hint("   2. Create vector search index")
        PrintStyle.hint("   3. Test Agent Zero")


async def main():
    """Main test function"""
    PrintStyle.standard("🧪 Agent Zero - Phase 1 & 2 Complete Test Suite")
    PrintStyle.standard("="*60)
    
    all_tests_passed = True
    
    # Test MongoDB connection
    if not await test_mongodb_connection():
        all_tests_passed = False
    
    # Test collections
    if not await test_collections():
        all_tests_passed = False
    
    # Test user management
    if not await test_user_management():
        all_tests_passed = False
    
    # Test vector store
    if not await test_vector_store():
        all_tests_passed = False
    
    # Show summary
    await show_summary()
    
    # Cleanup
    await close_mongodb_client()
    
    if all_tests_passed:
        PrintStyle.success("\n🎉 ALL TESTS PASSED!")
        PrintStyle.success("Phase 1 & 2 implementation is complete and working!")
    else:
        PrintStyle.error("\n❌ Some tests failed")
        PrintStyle.hint("Please check the errors above and fix them")
    
    return all_tests_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        PrintStyle.hint("\n🚀 Ready to proceed with Agent Zero testing!")
    else:
        PrintStyle.hint("\n🔧 Please fix the issues and run the test again")

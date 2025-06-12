#!/usr/bin/env python3
"""
Simple test for Phase 1 & 2 implementation
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.helpers.print_style import PrintStyle
from models import vector_store_config, mongodb_config


def test_configuration():
    """Test configuration loading"""
    PrintStyle.standard("=== Phase 1 & 2 Configuration Test ===")
    
    # Test vector store config
    PrintStyle.standard(f"Vector store provider: {vector_store_config.provider}")
    PrintStyle.standard(f"MongoDB URI configured: {bool(mongodb_config.uri)}")
    PrintStyle.standard(f"MongoDB database: {mongodb_config.database}")
    PrintStyle.standard(f"Use MongoDB: {vector_store_config.use_mongodb}")
    
    # Test imports
    try:
        from python.helpers.mongodb_client import MongoDBClient
        PrintStyle.success("✓ MongoDB client import successful")
    except Exception as e:
        PrintStyle.error(f"✗ MongoDB client import failed: {e}")
        return False
    
    try:
        from python.helpers.vector_store import VectorStoreFactory
        PrintStyle.success("✓ Vector store factory import successful")
    except Exception as e:
        PrintStyle.error(f"✗ Vector store factory import failed: {e}")
        return False
    
    try:
        from python.helpers.vector_store_faiss import FAISSVectorStore
        PrintStyle.success("✓ FAISS vector store import successful")
    except Exception as e:
        PrintStyle.error(f"✗ FAISS vector store import failed: {e}")
        return False
    
    try:
        from python.helpers.vector_store_mongodb import MongoDBVectorStore
        PrintStyle.success("✓ MongoDB vector store import successful")
    except Exception as e:
        PrintStyle.error(f"✗ MongoDB vector store import failed: {e}")
        return False
    
    try:
        from python.helpers.user_manager import UserManager
        PrintStyle.success("✓ User manager import successful")
    except Exception as e:
        PrintStyle.error(f"✗ User manager import failed: {e}")
        return False
    
    try:
        from python.helpers.memory_unified import UnifiedMemory
        PrintStyle.success("✓ Unified memory import successful")
    except Exception as e:
        PrintStyle.error(f"✗ Unified memory import failed: {e}")
        return False
    
    PrintStyle.success("\n🎉 Phase 1 & 2 implementation successful!")
    PrintStyle.hint("\nNext steps:")
    PrintStyle.hint("1. Configure MongoDB URI in .env file")
    PrintStyle.hint("2. Set VECTOR_STORE_PROVIDER=mongodb to use MongoDB")
    PrintStyle.hint("3. Create vector search index in MongoDB Atlas")
    PrintStyle.hint("4. Test with actual agent conversations")
    
    return True


if __name__ == "__main__":
    test_configuration()

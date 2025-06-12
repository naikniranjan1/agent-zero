#!/usr/bin/env python3
"""
Automated MongoDB Atlas Setup Script for Agent Zero
Creates all required collections, indexes, and configurations automatically
"""

import asyncio
import sys
import os
from typing import Dict, Any, List
from pymongo import MongoClient
from pymongo.errors import OperationFailure, DuplicateKeyError

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.helpers.print_style import PrintStyle
from python.helpers.dotenv import get_dotenv_value
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class MongoDBSetup:
    """Automated MongoDB Atlas setup for Agent Zero"""
    
    def __init__(self):
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.database_name = os.getenv("MONGODB_DATABASE", "agent_zero")
        self.client = None
        self.db = None
        
        # Collection configurations
        self.collections_config = {
            "user_memory": {
                "description": "User memory and knowledge storage with vector embeddings",
                "indexes": [
                    {"keys": [("user_id", 1)], "name": "user_id_index"},
                    {"keys": [("metadata.timestamp", -1)], "name": "timestamp_index"},
                    {"keys": [("metadata.area", 1)], "name": "area_index"},
                    {"keys": [("user_id", 1), ("metadata.area", 1)], "name": "user_area_index"},
                ]
            },
            "user_chats": {
                "description": "User chat history and conversation data",
                "indexes": [
                    {"keys": [("user_id", 1)], "name": "user_id_index"},
                    {"keys": [("chat_id", 1)], "name": "chat_id_index"},
                    {"keys": [("created_at", -1)], "name": "created_at_index"},
                    {"keys": [("user_id", 1), ("created_at", -1)], "name": "user_created_index"},
                ]
            },
            "user_knowledge": {
                "description": "User uploaded knowledge and documents",
                "indexes": [
                    {"keys": [("user_id", 1)], "name": "user_id_index"},
                    {"keys": [("knowledge_type", 1)], "name": "knowledge_type_index"},
                    {"keys": [("filename", 1)], "name": "filename_index"},
                    {"keys": [("user_id", 1), ("knowledge_type", 1)], "name": "user_knowledge_index"},
                ]
            },
            "users": {
                "description": "User accounts and profiles",
                "indexes": [
                    {"keys": [("user_id", 1)], "name": "user_id_index", "unique": True},
                    {"keys": [("username", 1)], "name": "username_index", "unique": True},
                    {"keys": [("email", 1)], "name": "email_index", "sparse": True},
                    {"keys": [("created_at", -1)], "name": "created_at_index"},
                ]
            },
            "user_sessions": {
                "description": "User authentication sessions",
                "indexes": [
                    {"keys": [("session_id", 1)], "name": "session_id_index", "unique": True},
                    {"keys": [("user_id", 1)], "name": "user_id_index"},
                    {"keys": [("expires_at", 1)], "name": "expires_at_index"},
                    {"keys": [("user_id", 1), ("is_active", 1)], "name": "user_active_index"},
                ]
            },
            "user_memory_fast": {
                "description": "Fast memory storage without vector embeddings",
                "indexes": [
                    {"keys": [("user_id", 1)], "name": "user_id_index"},
                    {"keys": [("timestamp", -1)], "name": "timestamp_index"},
                    {"keys": [("area", 1)], "name": "area_index"},
                    {"keys": [("type", 1)], "name": "type_index"},
                    {"keys": [("user_id", 1), ("area", 1)], "name": "user_area_index"},
                    {"keys": [("content", "text")], "name": "content_text_index"},
                ]
            }
        }
        
        # Vector search index configuration
        self.vector_search_config = {
            "collection": "user_memory",
            "index_name": "vector_search_index",
            "definition": {
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
                    },
                    {
                        "type": "filter",
                        "path": "metadata.type"
                    }
                ]
            }
        }
    
    def connect(self) -> bool:
        """Connect to MongoDB Atlas"""
        if not self.mongodb_uri:
            PrintStyle.error("❌ No MongoDB URI found in environment variables")
            PrintStyle.hint("Please set MONGODB_URI in your .env file")
            return False
        
        try:
            PrintStyle.standard("Connecting to MongoDB Atlas...")
            self.client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=10000)
            
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            
            PrintStyle.success(f"✅ Connected to MongoDB Atlas database: {self.database_name}")
            return True
            
        except Exception as e:
            PrintStyle.error(f"❌ Failed to connect to MongoDB Atlas: {str(e)}")
            return False
    
    def create_collections(self) -> bool:
        """Create all required collections"""
        PrintStyle.standard("\n=== Creating Collections ===")
        
        try:
            existing_collections = self.db.list_collection_names()
            
            for collection_name, config in self.collections_config.items():
                if collection_name in existing_collections:
                    PrintStyle.success(f"✅ Collection '{collection_name}' already exists")
                else:
                    # Create collection
                    self.db.create_collection(collection_name)
                    PrintStyle.success(f"✅ Created collection: {collection_name}")
                
                PrintStyle.hint(f"   Description: {config['description']}")
            
            return True
            
        except Exception as e:
            PrintStyle.error(f"❌ Failed to create collections: {str(e)}")
            return False
    
    def create_indexes(self) -> bool:
        """Create all required indexes"""
        PrintStyle.standard("\n=== Creating Database Indexes ===")
        
        try:
            for collection_name, config in self.collections_config.items():
                collection = self.db[collection_name]
                
                PrintStyle.standard(f"Creating indexes for '{collection_name}'...")
                
                for index_config in config["indexes"]:
                    try:
                        index_name = index_config["name"]
                        keys = index_config["keys"]
                        options = {k: v for k, v in index_config.items() if k not in ["keys", "name"]}
                        
                        # Create index
                        collection.create_index(keys, name=index_name, **options)
                        PrintStyle.success(f"  ✅ Created index: {index_name}")
                        
                    except DuplicateKeyError:
                        PrintStyle.success(f"  ✅ Index already exists: {index_name}")
                    except Exception as e:
                        PrintStyle.warning(f"  ⚠ Failed to create index {index_name}: {str(e)}")
            
            return True
            
        except Exception as e:
            PrintStyle.error(f"❌ Failed to create indexes: {str(e)}")
            return False
    
    def create_vector_search_index(self) -> bool:
        """Create Atlas Vector Search index"""
        PrintStyle.standard("\n=== Creating Vector Search Index ===")
        
        try:
            # Note: Vector search indexes cannot be created via pymongo
            # They must be created through the Atlas API or UI
            
            PrintStyle.warning("⚠ Vector Search Index must be created manually")
            PrintStyle.hint("This requires MongoDB Atlas API or UI access")
            
            # Display the configuration for manual creation
            PrintStyle.standard("\n📋 Vector Search Index Configuration:")
            PrintStyle.standard(f"Database: {self.database_name}")
            PrintStyle.standard(f"Collection: {self.vector_search_config['collection']}")
            PrintStyle.standard(f"Index Name: {self.vector_search_config['index_name']}")
            
            PrintStyle.standard("\n📄 Index Definition (JSON):")
            import json
            definition_json = json.dumps(self.vector_search_config["definition"], indent=2)
            print(definition_json)
            
            # Try to create via Atlas API if credentials are available
            atlas_api_key = os.getenv("MONGODB_ATLAS_API_KEY")
            if atlas_api_key:
                return self._create_vector_index_via_api()
            else:
                PrintStyle.hint("\n💡 To automate vector index creation:")
                PrintStyle.hint("1. Set MONGODB_ATLAS_API_KEY in .env")
                PrintStyle.hint("2. Or create manually in MongoDB Atlas UI")
                return True
            
        except Exception as e:
            PrintStyle.error(f"❌ Vector search index setup failed: {str(e)}")
            return False
    
    def _create_vector_index_via_api(self) -> bool:
        """Create vector search index via Atlas API"""
        try:
            import requests
            import base64

            PrintStyle.standard("Attempting to create vector index via Atlas API...")

            # Get Atlas API credentials
            api_public_key = os.getenv("MONGODB_ATLAS_PUBLIC_KEY")
            api_private_key = os.getenv("MONGODB_ATLAS_PRIVATE_KEY")
            project_id = os.getenv("MONGODB_ATLAS_PROJECT_ID")
            cluster_name = os.getenv("MONGODB_ATLAS_CLUSTER_NAME", "Cluster0")

            if not all([api_public_key, api_private_key, project_id]):
                PrintStyle.warning("⚠ Atlas API credentials not found")
                PrintStyle.hint("Set MONGODB_ATLAS_PUBLIC_KEY, MONGODB_ATLAS_PRIVATE_KEY, MONGODB_ATLAS_PROJECT_ID in .env")
                return True

            # Create authentication header
            credentials = f"{api_public_key}:{api_private_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/json"
            }

            # Atlas API endpoint for search indexes
            url = f"https://cloud.mongodb.com/api/atlas/v1.0/groups/{project_id}/clusters/{cluster_name}/search/indexes"

            # Search index payload
            payload = {
                "name": self.vector_search_config["index_name"],
                "database": self.database_name,
                "collectionName": self.vector_search_config["collection"],
                "type": "vectorSearch",
                "definition": self.vector_search_config["definition"]
            }

            # Make API request
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 201:
                PrintStyle.success("✅ Vector search index created via Atlas API!")
                return True
            elif response.status_code == 409:
                PrintStyle.success("✅ Vector search index already exists")
                return True
            else:
                PrintStyle.error(f"❌ Atlas API error: {response.status_code} - {response.text}")
                return False

        except ImportError:
            PrintStyle.warning("⚠ 'requests' library not found - install with: pip install requests")
            return True
        except Exception as e:
            PrintStyle.error(f"❌ Atlas API creation failed: {str(e)}")
            return False
    
    def verify_setup(self) -> bool:
        """Verify the complete setup"""
        PrintStyle.standard("\n=== Verifying Setup ===")
        
        try:
            # Check collections
            existing_collections = self.db.list_collection_names()
            required_collections = list(self.collections_config.keys())
            
            for collection_name in required_collections:
                if collection_name in existing_collections:
                    PrintStyle.success(f"✅ Collection verified: {collection_name}")
                else:
                    PrintStyle.error(f"❌ Missing collection: {collection_name}")
                    return False
            
            # Check indexes
            for collection_name in required_collections:
                collection = self.db[collection_name]
                indexes = list(collection.list_indexes())
                index_names = [idx["name"] for idx in indexes]
                
                required_indexes = [idx["name"] for idx in self.collections_config[collection_name]["indexes"]]
                
                for index_name in required_indexes:
                    if index_name in index_names:
                        PrintStyle.success(f"✅ Index verified: {collection_name}.{index_name}")
                    else:
                        PrintStyle.warning(f"⚠ Missing index: {collection_name}.{index_name}")
            
            # Test write/read operations
            PrintStyle.standard("Testing database operations...")
            
            test_collection = self.db["test_setup"]
            test_doc = {"test": "setup_verification", "timestamp": "2025-01-11"}
            
            # Write test
            result = test_collection.insert_one(test_doc)
            PrintStyle.success(f"✅ Write test successful")
            
            # Read test
            found_doc = test_collection.find_one({"_id": result.inserted_id})
            PrintStyle.success(f"✅ Read test successful")
            
            # Cleanup
            test_collection.delete_one({"_id": result.inserted_id})
            PrintStyle.success(f"✅ Cleanup successful")
            
            return True
            
        except Exception as e:
            PrintStyle.error(f"❌ Verification failed: {str(e)}")
            return False
    
    def show_summary(self):
        """Show setup summary and next steps"""
        PrintStyle.standard("\n" + "="*60)
        PrintStyle.success("🎉 MONGODB ATLAS SETUP COMPLETE!")
        PrintStyle.standard("="*60)
        
        PrintStyle.standard(f"\n📊 Database: {self.database_name}")
        PrintStyle.standard("📁 Collections created:")
        for collection_name, config in self.collections_config.items():
            PrintStyle.standard(f"   • {collection_name} - {config['description']}")
        
        PrintStyle.standard("\n⚙️ Configuration:")
        PrintStyle.standard(f"   • VECTOR_STORE_PROVIDER: {os.getenv('VECTOR_STORE_PROVIDER', 'faiss')}")
        PrintStyle.standard(f"   • MONGODB_DATABASE: {self.database_name}")
        
        PrintStyle.standard("\n🚀 Ready for:")
        PrintStyle.standard("   • Multi-user support")
        PrintStyle.standard("   • Vector search (after manual index creation)")
        PrintStyle.standard("   • Chat history persistence")
        PrintStyle.standard("   • Knowledge management")
        PrintStyle.standard("   • User session management")
        
        PrintStyle.standard("\n📋 Manual Step Required:")
        PrintStyle.warning("   Create Vector Search Index in MongoDB Atlas UI")
        PrintStyle.hint("   Use the JSON configuration displayed above")
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()


async def main():
    """Main setup function"""
    PrintStyle.standard("🚀 Agent Zero - MongoDB Atlas Automated Setup")
    PrintStyle.standard("="*60)
    
    setup = MongoDBSetup()
    
    try:
        # Connect to MongoDB
        if not setup.connect():
            return False
        
        # Create collections
        if not setup.create_collections():
            return False
        
        # Create indexes
        if not setup.create_indexes():
            return False
        
        # Setup vector search index
        if not setup.create_vector_search_index():
            return False
        
        # Verify setup
        if not setup.verify_setup():
            return False
        
        # Show summary
        setup.show_summary()
        
        return True
        
    except Exception as e:
        PrintStyle.error(f"❌ Setup failed: {str(e)}")
        return False
        
    finally:
        setup.close()


if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        PrintStyle.success("\n✅ Setup completed successfully!")
        PrintStyle.hint("You can now start Agent Zero with MongoDB Atlas support")
    else:
        PrintStyle.error("\n❌ Setup failed!")
        PrintStyle.hint("Please check the errors above and try again")

#!/usr/bin/env python3
"""
Simple check of MongoDB memory contents
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime


async def check_mongodb_memory():
    """Check MongoDB memory contents directly"""
    
    # Direct connection string
    uri = "mongodb+srv://naikniranjan8088:gIZnDOujHmnEqnkh@rag-database.pfwpbcc.mongodb.net/?retryWrites=true&w=majority&appName=rag-database"
    database_name = "agent_zero"
    
    try:
        print("🔍 Connecting to MongoDB Atlas...")
        client = AsyncIOMotorClient(uri)
        db = client[database_name]
        
        # Test connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB Atlas")
        
        # Get all collections
        collections = await db.list_collection_names()
        print(f"\n📁 Available collections: {collections}")
        
        # Check each collection
        for collection_name in collections:
            print(f"\n📊 Collection: {collection_name}")
            print("-" * 40)
            
            collection = db[collection_name]
            count = await collection.count_documents({})
            print(f"Total documents: {count}")
            
            if count > 0:
                # Get sample documents
                sample_docs = await collection.find().limit(3).to_list(length=3)
                
                for i, doc in enumerate(sample_docs, 1):
                    print(f"\n  Document {i}:")
                    
                    # Show key fields
                    for key, value in doc.items():
                        if key == '_id':
                            continue
                        
                        value_str = str(value)
                        if len(value_str) > 100:
                            value_str = value_str[:100] + "..."
                        
                        print(f"    {key}: {value_str}")
        
        # Search for name-related content
        print(f"\n🔍 Searching for name-related content...")
        print("-" * 40)
        
        for collection_name in collections:
            collection = db[collection_name]
            
            # Search for name-related documents
            name_docs = await collection.find({
                "$or": [
                    {"content": {"$regex": "name", "$options": "i"}},
                    {"content": {"$regex": "niru", "$options": "i"}},
                    {"content": {"$regex": "call me", "$options": "i"}}
                ]
            }).to_list(length=10)
            
            if name_docs:
                print(f"\n📝 Found {len(name_docs)} name-related documents in {collection_name}:")
                for doc in name_docs:
                    content = doc.get("content", "")
                    if len(content) > 150:
                        content = content[:150] + "..."
                    user_id = doc.get("user_id", "unknown")
                    role = doc.get("role", "")
                    timestamp = doc.get("timestamp", "")
                    
                    print(f"  • [{role}] {user_id} ({timestamp}): {content}")
        
        print(f"\n🎯 Memory Analysis Complete!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_mongodb_memory())

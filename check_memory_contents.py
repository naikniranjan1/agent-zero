#!/usr/bin/env python3
"""
Check what's stored in MongoDB long-term memory
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from python.helpers.mongodb_client import get_mongodb_client
from python.helpers.print_style import PrintStyle


async def check_memory_contents():
    """Check all memory collections and their contents"""
    try:
        PrintStyle.standard("🔍 Checking Long-Term Memory Contents")
        PrintStyle.standard("="*60)
        
        client = await get_mongodb_client()
        
        if not await client.test_connection():
            PrintStyle.error("❌ MongoDB connection failed")
            return
        
        db = client.get_database()
        
        # Get all collections
        collections = await db.list_collection_names()
        PrintStyle.standard(f"📁 Available collections: {collections}")
        
        # Check each memory-related collection
        memory_collections = [
            "user_chats",
            "user_memory_fast", 
            "user_memory",
            "user_knowledge",
            "users",
            "user_sessions"
        ]
        
        for collection_name in memory_collections:
            if collection_name in collections:
                await check_collection_contents(db, collection_name)
            else:
                PrintStyle.warning(f"⚠ Collection '{collection_name}' not found")
        
    except Exception as e:
        PrintStyle.error(f"❌ Error checking memory: {str(e)}")


async def check_collection_contents(db, collection_name):
    """Check contents of a specific collection"""
    try:
        PrintStyle.standard(f"\n📊 Collection: {collection_name}")
        PrintStyle.standard("-" * 40)
        
        collection = db[collection_name]
        
        # Get total count
        total_count = await collection.count_documents({})
        PrintStyle.standard(f"Total documents: {total_count}")
        
        if total_count == 0:
            PrintStyle.warning("  (Empty collection)")
            return
        
        # Get sample documents
        sample_docs = await collection.find().limit(5).to_list(length=5)
        
        # Group by user_id if available
        user_counts = {}
        if total_count > 0:
            pipeline = [
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            
            try:
                user_stats = await collection.aggregate(pipeline).to_list(length=None)
                for stat in user_stats:
                    user_id = stat["_id"] or "no_user_id"
                    count = stat["count"]
                    user_counts[user_id] = count
            except:
                pass
        
        if user_counts:
            PrintStyle.standard("📈 Documents per user:")
            for user_id, count in user_counts.items():
                PrintStyle.standard(f"  • {user_id}: {count} documents")
        
        # Show sample content
        PrintStyle.standard("\n📄 Sample documents:")
        for i, doc in enumerate(sample_docs, 1):
            PrintStyle.standard(f"\n  Document {i}:")
            
            # Show key fields
            key_fields = ["user_id", "content", "role", "timestamp", "area", "type"]
            for field in key_fields:
                if field in doc:
                    value = str(doc[field])
                    if len(value) > 100:
                        value = value[:100] + "..."
                    PrintStyle.standard(f"    {field}: {value}")
            
            # Show any other interesting fields
            other_fields = [k for k in doc.keys() if k not in key_fields and not k.startswith('_')]
            if other_fields:
                PrintStyle.standard(f"    other_fields: {other_fields}")
        
    except Exception as e:
        PrintStyle.error(f"❌ Error checking collection {collection_name}: {str(e)}")


async def search_for_names():
    """Search specifically for name-related information"""
    try:
        PrintStyle.standard(f"\n🔍 Searching for Name Information")
        PrintStyle.standard("-" * 40)
        
        client = await get_mongodb_client()
        db = client.get_database()
        
        # Search in user_chats
        chats_collection = db["user_chats"]
        if await chats_collection.count_documents({}) > 0:
            name_chats = await chats_collection.find({
                "content": {"$regex": "name|niru|call me", "$options": "i"}
            }).to_list(length=10)
            
            if name_chats:
                PrintStyle.success(f"📝 Found {len(name_chats)} chat messages about names:")
                for chat in name_chats:
                    content = chat.get("content", "")[:100]
                    role = chat.get("role", "unknown")
                    user_id = chat.get("user_id", "unknown")
                    PrintStyle.standard(f"  • [{role}] {user_id}: {content}...")
        
        # Search in user_memory_fast
        memory_collection = db["user_memory_fast"]
        if await memory_collection.count_documents({}) > 0:
            name_memories = await memory_collection.find({
                "content": {"$regex": "name|niru|call me", "$options": "i"}
            }).to_list(length=10)
            
            if name_memories:
                PrintStyle.success(f"🧠 Found {len(name_memories)} memories about names:")
                for memory in name_memories:
                    content = memory.get("content", "")[:150]
                    user_id = memory.get("user_id", "unknown")
                    area = memory.get("area", "unknown")
                    PrintStyle.standard(f"  • [{area}] {user_id}: {content}...")
        
    except Exception as e:
        PrintStyle.error(f"❌ Error searching for names: {str(e)}")


async def show_recent_activity():
    """Show recent activity across all collections"""
    try:
        PrintStyle.standard(f"\n⏰ Recent Activity (Last 24 hours)")
        PrintStyle.standard("-" * 40)
        
        client = await get_mongodb_client()
        db = client.get_database()
        
        # Check recent activity in each collection
        collections_to_check = ["user_chats", "user_memory_fast"]
        
        for collection_name in collections_to_check:
            try:
                collection = db[collection_name]
                
                # Get recent documents (last 24 hours)
                from datetime import timedelta
                yesterday = datetime.utcnow() - timedelta(days=1)
                
                recent_docs = await collection.find({
                    "timestamp": {"$gte": yesterday}
                }).sort("timestamp", -1).limit(5).to_list(length=5)
                
                if recent_docs:
                    PrintStyle.success(f"📅 Recent activity in {collection_name}:")
                    for doc in recent_docs:
                        timestamp = doc.get("timestamp", "unknown")
                        content = str(doc.get("content", ""))[:80]
                        user_id = doc.get("user_id", "unknown")
                        PrintStyle.standard(f"  • {timestamp} [{user_id}]: {content}...")
                else:
                    PrintStyle.warning(f"⚠ No recent activity in {collection_name}")
                    
            except Exception as e:
                PrintStyle.warning(f"⚠ Could not check {collection_name}: {str(e)}")
        
    except Exception as e:
        PrintStyle.error(f"❌ Error checking recent activity: {str(e)}")


async def main():
    """Main function"""
    await check_memory_contents()
    await search_for_names()
    await show_recent_activity()
    
    PrintStyle.standard("\n" + "="*60)
    PrintStyle.success("🎯 Memory Analysis Complete!")
    PrintStyle.standard("="*60)


if __name__ == "__main__":
    asyncio.run(main())

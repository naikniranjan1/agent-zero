
import asyncio
from python.helpers.mongodb_client import get_mongodb_client

async def create_indexes():
    try:
        client = await get_mongodb_client()
        
        # Create text index on user_chats collection
        chats_collection = client.get_collection("user_chats")
        if chats_collection:
            # Create text index for fast content search
            await chats_collection.create_index([("content", "text")])
            print("✅ Created text index on user_chats.content")
            
            # Create compound index for fast user queries
            await chats_collection.create_index([
                ("user_id", 1), 
                ("timestamp", -1)
            ])
            print("✅ Created compound index on user_chats")
            
            # Create chat_id index
            await chats_collection.create_index([("chat_id", 1)])
            print("✅ Created chat_id index on user_chats")
        
        print("🎉 All indexes created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")

if __name__ == "__main__":
    asyncio.run(create_indexes())

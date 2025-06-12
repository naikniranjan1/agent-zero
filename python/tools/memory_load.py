from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle

DEFAULT_THRESHOLD = 0.7
DEFAULT_LIMIT = 10


class MemoryLoad(Tool):
    """Fast Memory Load Tool - MongoDB-only, no vector dependencies"""

    async def execute(self, query="", threshold=DEFAULT_THRESHOLD, limit=DEFAULT_LIMIT, filter="", **kwargs):
        try:
            # Get user ID from agent context (for multi-user support)
            user_id = getattr(self.agent, 'user_id', None) or getattr(self.agent.context, 'user_id', None) or "default"

            PrintStyle.hint(f"🔍 Searching memory for: '{query}' (user: {user_id})")

            # Search fast memory storage first
            fast_memories = await self._search_fast_memory(query, user_id, limit)

            if fast_memories:
                # Format memories for response
                text = "\n\n".join([mem.get('content', str(mem)) for mem in fast_memories])
                result = f"Found in memory:\n\n{text}"
                PrintStyle.success(f"✅ Found {len(fast_memories)} memories")
            else:
                # Search conversation history
                recent_context = await self._search_conversation_history(query, user_id)
                if recent_context:
                    result = f"From recent conversations:\n\n{recent_context}"
                    PrintStyle.success("✅ Found in conversation history")
                else:
                    result = f"I don't have any specific information about '{query}' in my memory. Could you tell me more about it so I can remember it for next time?"
                    PrintStyle.warning("⚠ No memories found")

            return Response(message=result, break_loop=False)

        except Exception as e:
            PrintStyle.error(f"Memory load error: {str(e)}")
            # Simple fallback response
            result = f"I'm having trouble accessing my memory right now, but I don't recall specific information about '{query}'. Could you remind me?"
            return Response(message=result, break_loop=False)

    async def _search_fast_memory(self, query: str, user_id: str, limit: int) -> list:
        """Search fast memory storage (MongoDB only)"""
        try:
            from python.helpers.mongodb_client import get_mongodb_client

            client = await get_mongodb_client()
            collection = client.get_collection("user_memory_fast")

            if collection is None:
                PrintStyle.warning("⚠ Fast memory collection not available")
                return []

            # Search for memories containing query terms
            query_words = query.lower().split()

            # Special handling for name queries
            if "name" in query.lower():
                search_patterns = [
                    "name",
                    "call me",
                    "i am",
                    "my name is",
                    "i'm"
                ]
                search_pattern = "|".join(search_patterns)
            else:
                search_pattern = "|".join([word for word in query_words if len(word) > 2])

            if not search_pattern:
                return []

            # Find relevant memories
            search_query = {
                "user_id": user_id,
                "content": {"$regex": search_pattern, "$options": "i"}
            }

            cursor = collection.find(search_query).sort("timestamp", -1).limit(limit)
            memories = []

            async for doc in cursor:
                content = doc.get("content", "")
                metadata = doc.get("metadata", {})
                if content and len(content) > 5:
                    memories.append({
                        "content": content,
                        "metadata": metadata,
                        "timestamp": doc.get("timestamp"),
                        "area": doc.get("area", "main")
                    })

            return memories

        except Exception as e:
            PrintStyle.warning(f"Fast memory search failed: {str(e)}")
            return []

    async def _search_conversation_history(self, query: str, user_id: str) -> str:
        """Search conversation history for relevant information"""
        try:
            from python.helpers.mongodb_client import get_mongodb_client

            client = await get_mongodb_client()
            collection = client.get_collection("user_chats")

            if collection is None:
                return ""

            # Search recent conversations for the query terms
            query_words = query.lower().split()
            search_pattern = "|".join([word for word in query_words if len(word) > 2])

            if not search_pattern:
                return ""

            # Find relevant messages
            search_query = {
                "user_id": user_id,
                "content": {"$regex": search_pattern, "$options": "i"}
            }

            cursor = collection.find(search_query).sort("timestamp", -1).limit(5)
            messages = []

            async for doc in cursor:
                content = doc.get("content", "")
                role = doc.get("role", "user")
                if content and len(content) > 10:
                    messages.append(f"{role}: {content}")

            if messages:
                return "\n".join(messages)

            return ""

        except Exception as e:
            PrintStyle.warning(f"Conversation history search failed: {str(e)}")
            return ""

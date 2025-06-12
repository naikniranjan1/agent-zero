from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle

DEFAULT_THRESHOLD = 0.7


class MemoryForget(Tool):
    """Smart Memory Forget Tool - Removes memories from fast storage"""

    async def execute(self, query="", threshold=DEFAULT_THRESHOLD, filter="", **kwargs):
        try:
            # Get user ID
            user_id = getattr(self.agent, 'user_id', None) or getattr(self.agent.context, 'user_id', None)

            # Delete from fast storage
            deleted_count = await self._delete_from_fast_storage(query, user_id)

            # Try to delete from vector storage too (if available)
            vector_deleted = await self._delete_from_vector_storage(query, user_id)

            total_deleted = deleted_count + vector_deleted

            result = self.agent.read_prompt("fw.memories_deleted.md", memory_count=total_deleted)
            return Response(message=result, break_loop=False)

        except Exception as e:
            PrintStyle.error(f"Memory forget error: {str(e)}")
            return Response(message="I had trouble forgetting that specific information, but I'll try to avoid referencing it.", break_loop=False)

    async def _delete_from_fast_storage(self, query: str, user_id: str) -> int:
        """Delete memories from fast MongoDB storage"""
        try:
            from python.helpers.mongodb_client import get_mongodb_client

            client = await get_mongodb_client()
            collection = client.get_collection("user_memory_fast")

            if collection is None:
                return 0

            # Create search pattern
            query_words = query.lower().split()
            search_pattern = "|".join([word for word in query_words if len(word) > 2])

            if not search_pattern:
                return 0

            # Delete matching documents
            delete_query = {
                "user_id": user_id,
                "content": {"$regex": search_pattern, "$options": "i"}
            }

            result = await collection.delete_many(delete_query)
            return result.deleted_count

        except Exception as e:
            PrintStyle.error(f"Fast storage delete failed: {str(e)}")
            return 0

    async def _delete_from_vector_storage(self, query: str, user_id: str) -> int:
        """Delete memories from vector storage (if available)"""
        try:
            from python.helpers.memory_unified import UnifiedMemory

            # Try to get vector memory
            vector_memory = await UnifiedMemory.get(self.agent, user_id=user_id)

            # Search for matching documents
            docs = await vector_memory.search_similarity_threshold(
                query=query,
                limit=10,
                threshold=0.5
            )

            if docs:
                # Extract document IDs
                doc_ids = [doc.metadata.get("id") for doc in docs if doc.metadata.get("id")]

                if doc_ids:
                    # Delete documents
                    success = await vector_memory.delete_documents(doc_ids)
                    return len(doc_ids) if success else 0

            return 0

        except Exception as e:
            PrintStyle.warning(f"Vector storage delete failed: {str(e)}")
            return 0

from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle


class MemoryDelete(Tool):
    """Smart Memory Delete Tool - Deletes specific memories by ID"""

    async def execute(self, ids="", **kwargs):
        try:
            if not ids.strip():
                return Response(message="No memory IDs provided to delete.", break_loop=False)

            # Get user ID
            user_id = getattr(self.agent, 'user_id', None) or getattr(self.agent.context, 'user_id', None)

            # Parse IDs
            id_list = [id.strip() for id in ids.split(",") if id.strip()]

            # Delete from fast storage
            fast_deleted = await self._delete_from_fast_storage(id_list, user_id)

            # Delete from vector storage
            vector_deleted = await self._delete_from_vector_storage(id_list, user_id)

            total_deleted = fast_deleted + vector_deleted

            result = self.agent.read_prompt("fw.memories_deleted.md", memory_count=total_deleted)
            return Response(message=result, break_loop=False)

        except Exception as e:
            PrintStyle.error(f"Memory delete error: {str(e)}")
            return Response(message="I had trouble deleting those specific memories.", break_loop=False)

    async def _delete_from_fast_storage(self, ids: list, user_id: str) -> int:
        """Delete memories from fast MongoDB storage"""
        try:
            from python.helpers.mongodb_client import get_mongodb_client

            client = await get_mongodb_client()
            collection = client.get_collection("user_memory_fast")

            if collection is None:
                return 0

            # Delete documents by ID
            delete_query = {
                "_id": {"$in": ids},
                "user_id": user_id
            }

            result = await collection.delete_many(delete_query)
            return result.deleted_count

        except Exception as e:
            PrintStyle.error(f"Fast storage delete failed: {str(e)}")
            return 0

    async def _delete_from_vector_storage(self, ids: list, user_id: str) -> int:
        """Delete memories from vector storage"""
        try:
            from python.helpers.memory_unified import UnifiedMemory

            # Try to get vector memory
            vector_memory = await UnifiedMemory.get(self.agent, user_id=user_id)

            # Delete documents
            success = await vector_memory.delete_documents(ids)
            return len(ids) if success else 0

        except Exception as e:
            PrintStyle.warning(f"Vector storage delete failed: {str(e)}")
            return 0

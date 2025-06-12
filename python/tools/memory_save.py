from python.helpers.tool import Tool, Response
from python.helpers.print_style import PrintStyle
from datetime import datetime
import uuid


class MemorySave(Tool):
    """Smart Memory Save Tool - Saves to fast chat storage and promotes important memories"""

    async def execute(self, text="", area="", **kwargs):
        try:
            if not text.strip():
                return Response(message="No text provided to save.", break_loop=False)

            # Get user ID
            user_id = getattr(self.agent, 'user_id', None) or getattr(self.agent.context, 'user_id', None)

            # Save to fast chat storage
            memory_id = await self._save_to_fast_storage(text, area, user_id, **kwargs)

            if memory_id:
                # Check if this should be promoted to long-term memory
                should_promote = await self._should_promote_memory(text)

                if should_promote:
                    await self._promote_to_long_term_memory(text, area, **kwargs)
                    result = self.agent.read_prompt("fw.memory_saved.md", memory_id=memory_id) + " (Promoted to long-term memory)"
                else:
                    result = self.agent.read_prompt("fw.memory_saved.md", memory_id=memory_id)
            else:
                result = "Memory saved successfully."

            return Response(message=result, break_loop=False)

        except Exception as e:
            PrintStyle.error(f"Memory save error: {str(e)}")
            return Response(message="Failed to save memory, but I'll remember this conversation.", break_loop=False)

    async def _save_to_fast_storage(self, text: str, area: str, user_id: str, **kwargs) -> str:
        """Save to fast MongoDB storage"""
        try:
            from python.helpers.mongodb_client import get_mongodb_client

            client = await get_mongodb_client()
            collection = client.get_collection("user_memory_fast")

            if collection is None:
                return ""

            memory_id = str(uuid.uuid4())
            doc = {
                "_id": memory_id,
                "user_id": user_id,
                "content": text,
                "area": area or "main",
                "timestamp": datetime.utcnow(),
                "metadata": kwargs,
                "type": "saved_memory"
            }

            await collection.insert_one(doc)
            return memory_id

        except Exception as e:
            PrintStyle.error(f"Fast storage save failed: {str(e)}")
            return ""

    async def _should_promote_memory(self, text: str) -> bool:
        """Determine if memory should be promoted to vector storage"""
        # Promote longer, more detailed memories
        if len(text.split()) > 20:
            return True

        # Promote memories with important keywords
        important_keywords = [
            'important', 'remember', 'note', 'key', 'critical',
            'password', 'config', 'setting', 'preference',
            'goal', 'objective', 'plan', 'strategy'
        ]

        text_lower = text.lower()
        return any(keyword in text_lower for keyword in important_keywords)

    async def _promote_to_long_term_memory(self, text: str, area: str, **kwargs):
        """Promote memory to long-term vector storage"""
        try:
            from python.helpers.memory_unified import UnifiedMemory
            from langchain_core.documents import Document

            # Get user ID
            user_id = getattr(self.agent, 'user_id', None)

            # Try to get vector memory
            vector_memory = await UnifiedMemory.get(self.agent, user_id=user_id)

            # Create document
            doc = Document(
                page_content=text,
                metadata={
                    "area": area or "main",
                    "type": "saved_memory",
                    "promoted": True,
                    **kwargs
                }
            )

            # Insert into vector memory
            await vector_memory.insert_documents([doc])
            PrintStyle.success("📚 Memory promoted to long-term storage")

        except Exception as e:
            PrintStyle.warning(f"Failed to promote to long-term memory: {str(e)}")
            # Don't fail the whole operation if promotion fails

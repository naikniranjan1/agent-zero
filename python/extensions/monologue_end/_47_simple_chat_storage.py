"""
Simple Chat Storage Extension
Stores every conversation to MongoDB for persistence
"""

import asyncio
from datetime import datetime
from python.helpers.extension import Extension
from agent import LoopData
from python.helpers.print_style import PrintStyle


class SimpleChatStorage(Extension):
    """Simple, reliable chat storage to MongoDB"""
    
    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        """Store conversation to MongoDB"""

        try:
            # Get conversation messages
            user_message = loop_data.user_message.output_text() if loop_data.user_message else ""

            # Get agent's response from the current loop
            agent_response = self._get_agent_response_from_loop(loop_data)

            if not user_message.strip():
                return

            # Get user ID
            user_id = getattr(self.agent, 'user_id', None) or getattr(self.agent.context, 'user_id', None) or "default"
            chat_id = getattr(self.agent.context, 'id', 'default_chat')

            PrintStyle.hint(f"💬 Storing: User='{user_message[:50]}...' Agent='{agent_response[:50]}...'")

            # Store both messages
            await self._store_message(user_message, "user", user_id, chat_id)

            if agent_response.strip():
                await self._store_message(agent_response, "assistant", user_id, chat_id)

            # Also store in fast memory if it contains important info
            await self._store_important_info(user_message, agent_response, user_id)

            PrintStyle.success(f"💾 Stored conversation (user: {user_id})")

        except Exception as e:
            PrintStyle.error(f"Chat storage error: {str(e)}")
    
    async def _store_message(self, content: str, role: str, user_id: str, chat_id: str):
        """Store a single message to MongoDB"""
        try:
            from python.helpers.mongodb_client import get_mongodb_client
            
            client = await get_mongodb_client()
            collection = client.get_collection("user_chats")
            
            if collection is None:
                PrintStyle.warning("⚠ Chat collection not available")
                return
            
            # Create message document
            message_doc = {
                "user_id": user_id,
                "chat_id": chat_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow(),
                "metadata": {
                    "length": len(content),
                    "word_count": len(content.split())
                }
            }
            
            # Insert message
            await collection.insert_one(message_doc)
            
        except Exception as e:
            PrintStyle.error(f"Failed to store message: {str(e)}")
    
    async def _store_important_info(self, user_message: str, agent_response: str, user_id: str):
        """Store important information to fast memory"""
        try:
            # Check if conversation contains important information
            important_keywords = [
                'name is', 'my name', 'call me', 'i am', "i'm",
                'remember', 'important', 'note', 'save',
                'prefer', 'like', 'love', 'hate', 'favorite',
                'birthday', 'age', 'location', 'work', 'job',
                'email', 'phone', 'address', 'password'
            ]
            
            combined_text = (user_message + " " + agent_response).lower()
            
            # Check if any important keywords are present
            has_important_info = any(keyword in combined_text for keyword in important_keywords)
            
            if has_important_info:
                await self._save_to_fast_memory(user_message, agent_response, user_id)
        
        except Exception as e:
            PrintStyle.error(f"Failed to store important info: {str(e)}")
    
    async def _save_to_fast_memory(self, user_message: str, agent_response: str, user_id: str):
        """Save important conversation to fast memory"""
        try:
            from python.helpers.mongodb_client import get_mongodb_client
            import uuid
            
            client = await get_mongodb_client()
            collection = client.get_collection("user_memory_fast")
            
            if collection is None:
                # Create the collection if it doesn't exist
                db = client.get_database()
                await db.create_collection("user_memory_fast")
                collection = client.get_collection("user_memory_fast")
            
            # Create memory document with better format
            if "name" in user_message.lower() or "call me" in user_message.lower():
                # Special handling for name information
                memory_content = f"User's name information: {user_message}"
                if agent_response:
                    memory_content += f" (Agent acknowledged: {agent_response})"
            else:
                # General conversation format
                memory_content = f"User: {user_message}"
                if agent_response:
                    memory_content += f"\nAssistant: {agent_response}"
            
            memory_doc = {
                "_id": str(uuid.uuid4()),
                "user_id": user_id,
                "content": memory_content,
                "area": "conversation",
                "type": "important_chat",
                "timestamp": datetime.utcnow(),
                "metadata": {
                    "user_message": user_message[:200],
                    "agent_response": agent_response[:200],
                    "auto_saved": True
                }
            }
            
            # Insert memory
            await collection.insert_one(memory_doc)
            PrintStyle.success("📚 Saved important info to fast memory")
            
        except Exception as e:
            PrintStyle.error(f"Failed to save to fast memory: {str(e)}")
    
    def _get_agent_response_from_loop(self, loop_data: LoopData) -> str:
        """Get agent response from the current loop data"""
        try:
            # Try to get from loop data first
            if hasattr(loop_data, 'agent_response') and loop_data.agent_response:
                return str(loop_data.agent_response)

            # Try to get the last response from agent
            if hasattr(self.agent, 'last_response') and self.agent.last_response:
                response = str(self.agent.last_response)
                # Clean up the response if it contains JSON
                if response.startswith('{"') and '"text"' in response:
                    try:
                        import json
                        response_data = json.loads(response)
                        return response_data.get('text', response)
                    except:
                        pass
                return response

            # Fallback to history
            return self._get_latest_agent_response()

        except Exception as e:
            PrintStyle.error(f"Failed to get agent response from loop: {str(e)}")
            return ""

    def _get_latest_agent_response(self) -> str:
        """Get the latest agent response from history"""
        try:
            # Get the last response from agent history
            history = self.agent.history.output()

            # Look for the most recent assistant message
            for message in reversed(history):
                if hasattr(message, 'role') and message.role == 'assistant':
                    return message.content
                elif hasattr(message, 'content'):
                    content = str(message.content)
                    # Check if it's an agent response
                    if 'Agent' in content and ':' in content:
                        return content.split(':', 1)[1].strip()

            return ""

        except Exception as e:
            PrintStyle.error(f"Failed to get agent response: {str(e)}")
            return ""

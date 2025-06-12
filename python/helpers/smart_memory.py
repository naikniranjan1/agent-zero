"""
Super-Fast Hybrid Memory System for Agent Zero
Intelligently routes queries to the fastest appropriate storage
"""

import re
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from langchain_core.documents import Document

from agent import Agent
from python.helpers.mongodb_client import get_mongodb_client
from python.helpers.memory_unified import UnifiedMemory, MemoryArea
from python.helpers.print_style import PrintStyle


class QueryType(Enum):
    """Types of queries for smart routing"""
    SIMPLE_CHAT = "simple_chat"          # Greetings, thanks, simple responses
    RECENT_CONTEXT = "recent_context"    # "What did we just discuss?"
    MEMORY_SEARCH = "memory_search"      # "Remember when we talked about X?"
    COMPLEX_TASK = "complex_task"        # Multi-step tasks requiring context


class MessageClassifier:
    """Classifies messages to determine optimal data retrieval strategy"""
    
    # Simple patterns that don't need memory search
    SIMPLE_PATTERNS = [
        r'^(hi|hey|hello|yo)\b',
        r'^(thanks?|thank you|thx)\b',
        r'^(ok|okay|yes|no|sure)\b',
        r'^(bye|goodbye|see you)\b',
        r'^(good morning|good afternoon|good evening)\b',
        r'^\w{1,3}$',  # Very short responses
    ]
    
    # Patterns that indicate recent context queries
    RECENT_PATTERNS = [
        r'\b(just|recently|earlier|before|previous|last)\b',
        r'\b(what did|what were|what was)\b.*\b(we|you|i)\b',
        r'\b(continue|keep going|go on)\b',
        r'\b(that|this|it)\b.*\b(above|before|earlier)\b',
    ]
    
    # Patterns that indicate memory search needed
    MEMORY_PATTERNS = [
        r'\b(remember|recall|mentioned|discussed|talked about)\b',
        r'\b(last time|before|previously|earlier)\b.*\b(said|told|discussed)\b',
        r'\b(what do you know about|tell me about)\b',
        r'\b(have we|did we|have i|did i)\b.*\b(before|previously)\b',
    ]
    
    @classmethod
    def classify_message(cls, message: str) -> QueryType:
        """Classify message to determine optimal retrieval strategy"""
        message_lower = message.lower().strip()
        
        # Check for simple chat patterns
        for pattern in cls.SIMPLE_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return QueryType.SIMPLE_CHAT
        
        # Check for recent context patterns
        for pattern in cls.RECENT_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return QueryType.RECENT_CONTEXT
        
        # Check for memory search patterns
        for pattern in cls.MEMORY_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return QueryType.MEMORY_SEARCH
        
        # Default to complex task for longer messages
        if len(message.split()) > 10:
            return QueryType.COMPLEX_TASK
        
        return QueryType.RECENT_CONTEXT


class FastChatStorage:
    """Lightning-fast chat storage without embeddings"""
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
        self.collection_name = "user_chats"
    
    async def store_message(
        self, 
        message: str, 
        role: str = "user",
        chat_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store chat message directly in MongoDB (no embeddings)"""
        try:
            client = await get_mongodb_client()
            collection = client.get_collection(self.collection_name)
            
            if not collection:
                return ""
            
            doc = {
                "chat_id": chat_id or "default",
                "user_id": self.user_id,
                "role": role,
                "content": message,
                "timestamp": datetime.utcnow(),
                "metadata": metadata or {}
            }
            
            result = await collection.insert_one(doc)
            return str(result.inserted_id)
            
        except Exception as e:
            PrintStyle.error(f"Failed to store chat message: {str(e)}")
            return ""
    
    async def get_recent_messages(
        self, 
        limit: int = 20,
        chat_id: Optional[str] = None,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get recent chat messages (super fast - no embeddings)"""
        try:
            client = await get_mongodb_client()
            collection = client.get_collection(self.collection_name)
            
            if not collection:
                return []
            
            # Build query
            query = {"user_id": self.user_id} if self.user_id else {}
            if chat_id:
                query["chat_id"] = chat_id
            
            # Only get recent messages
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            query["timestamp"] = {"$gte": cutoff_time}
            
            # Get messages sorted by timestamp
            cursor = collection.find(query).sort("timestamp", -1).limit(limit)
            messages = []
            
            async for doc in cursor:
                messages.append({
                    "role": doc.get("role", "user"),
                    "content": doc.get("content", ""),
                    "timestamp": doc.get("timestamp"),
                    "metadata": doc.get("metadata", {})
                })
            
            return list(reversed(messages))  # Return in chronological order
            
        except Exception as e:
            PrintStyle.error(f"Failed to get recent messages: {str(e)}")
            return []
    
    async def search_recent_content(
        self, 
        keywords: List[str],
        limit: int = 10,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Search recent messages by keywords (fast text search)"""
        try:
            client = await get_mongodb_client()
            collection = client.get_collection(self.collection_name)
            
            if not collection:
                return []
            
            # Build text search query
            search_terms = " ".join(keywords)
            query = {
                "user_id": self.user_id,
                "$text": {"$search": search_terms},
                "timestamp": {"$gte": datetime.utcnow() - timedelta(hours=hours_back)}
            }
            
            cursor = collection.find(query).sort("timestamp", -1).limit(limit)
            messages = []
            
            async for doc in cursor:
                messages.append({
                    "role": doc.get("role", "user"),
                    "content": doc.get("content", ""),
                    "timestamp": doc.get("timestamp"),
                    "score": doc.get("score", 1.0)
                })
            
            return messages
            
        except Exception as e:
            # Fallback to regex search if text index doesn't exist
            return await self._fallback_keyword_search(keywords, limit, hours_back)
    
    async def _fallback_keyword_search(
        self, 
        keywords: List[str], 
        limit: int, 
        hours_back: int
    ) -> List[Dict[str, Any]]:
        """Fallback keyword search using regex"""
        try:
            client = await get_mongodb_client()
            collection = client.get_collection(self.collection_name)
            
            if not collection:
                return []
            
            # Create regex pattern for keywords
            pattern = "|".join([re.escape(kw) for kw in keywords])
            query = {
                "user_id": self.user_id,
                "content": {"$regex": pattern, "$options": "i"},
                "timestamp": {"$gte": datetime.utcnow() - timedelta(hours=hours_back)}
            }
            
            cursor = collection.find(query).sort("timestamp", -1).limit(limit)
            messages = []
            
            async for doc in cursor:
                messages.append({
                    "role": doc.get("role", "user"),
                    "content": doc.get("content", ""),
                    "timestamp": doc.get("timestamp")
                })
            
            return messages
            
        except Exception as e:
            PrintStyle.error(f"Fallback keyword search failed: {str(e)}")
            return []


class SmartMemoryRouter:
    """Super-fast memory system with intelligent routing"""
    
    def __init__(self, agent: Agent, user_id: Optional[str] = None):
        self.agent = agent
        self.user_id = user_id
        self.fast_chat = FastChatStorage(user_id)
        self._vector_memory: Optional[UnifiedMemory] = None
        self._classifier = MessageClassifier()
    
    async def _get_vector_memory(self) -> UnifiedMemory:
        """Lazy load vector memory only when needed"""
        if self._vector_memory is None:
            self._vector_memory = await UnifiedMemory.get(self.agent, self.user_id)
        return self._vector_memory
    
    async def process_query(
        self, 
        query: str, 
        chat_history: Optional[List[str]] = None
    ) -> Tuple[List[Document], str]:
        """Smart query processing with optimal routing"""
        
        # Classify the query
        query_type = self._classifier.classify_message(query)
        
        PrintStyle.hint(f"🧠 Query classified as: {query_type.value}")
        
        if query_type == QueryType.SIMPLE_CHAT:
            return await self._handle_simple_chat(query)
        
        elif query_type == QueryType.RECENT_CONTEXT:
            return await self._handle_recent_context(query)
        
        elif query_type == QueryType.MEMORY_SEARCH:
            return await self._handle_memory_search(query)
        
        else:  # COMPLEX_TASK
            return await self._handle_complex_task(query)
    
    async def _handle_simple_chat(self, query: str) -> Tuple[List[Document], str]:
        """Handle simple chat - no memory search needed"""
        PrintStyle.success("⚡ Fast path: Simple chat (no memory search)")
        
        # Just get last few messages for context
        recent = await self.fast_chat.get_recent_messages(limit=3, hours_back=1)
        
        context = "Recent conversation:\n"
        for msg in recent[-3:]:
            context += f"{msg['role']}: {msg['content']}\n"
        
        return [], context
    
    async def _handle_recent_context(self, query: str) -> Tuple[List[Document], str]:
        """Handle recent context queries - fast MongoDB search"""
        PrintStyle.success("⚡ Fast path: Recent context search")
        
        # Extract keywords from query
        keywords = self._extract_keywords(query)
        
        # Search recent messages
        recent_messages = await self.fast_chat.get_recent_messages(limit=10, hours_back=6)
        
        if keywords:
            # Also search by keywords in recent timeframe
            keyword_results = await self.fast_chat.search_recent_content(
                keywords=keywords, 
                limit=5, 
                hours_back=6
            )
            
            # Combine and deduplicate
            all_messages = recent_messages + keyword_results
            seen_content = set()
            unique_messages = []
            
            for msg in all_messages:
                if msg['content'] not in seen_content:
                    unique_messages.append(msg)
                    seen_content.add(msg['content'])
        else:
            unique_messages = recent_messages
        
        # Format context
        context = "Recent relevant conversation:\n"
        for msg in unique_messages[-8:]:
            context += f"{msg['role']}: {msg['content']}\n"
        
        return [], context
    
    async def _handle_memory_search(self, query: str) -> Tuple[List[Document], str]:
        """Handle memory search - use vector search when needed"""
        PrintStyle.warning("🔍 Vector path: Memory search required")
        
        # Use vector memory for semantic search
        vector_memory = await self._get_vector_memory()
        
        # Search memories
        memories = await vector_memory.search_similarity_threshold(
            query=query,
            limit=5,
            threshold=0.6,
            area=MemoryArea.MAIN
        )
        
        # Also get some recent context
        recent = await self.fast_chat.get_recent_messages(limit=5, hours_back=12)
        
        context = "Recent context:\n"
        for msg in recent[-3:]:
            context += f"{msg['role']}: {msg['content']}\n"
        
        if memories:
            context += "\nRelevant memories:\n"
            for memory in memories:
                context += f"- {memory.page_content}\n"
        
        return memories, context
    
    async def _handle_complex_task(self, query: str) -> Tuple[List[Document], str]:
        """Handle complex tasks - hybrid approach"""
        PrintStyle.standard("🔄 Hybrid path: Complex task processing")
        
        # Get recent context (fast)
        recent = await self.fast_chat.get_recent_messages(limit=8, hours_back=6)
        
        # Get relevant memories (slower but needed)
        vector_memory = await self._get_vector_memory()
        memories = await vector_memory.search_similarity_threshold(
            query=query,
            limit=3,
            threshold=0.7
        )
        
        # Combine contexts
        context = "Recent conversation:\n"
        for msg in recent[-5:]:
            context += f"{msg['role']}: {msg['content']}\n"
        
        if memories:
            context += "\nRelevant background:\n"
            for memory in memories:
                context += f"- {memory.page_content}\n"
        
        return memories, context
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text"""
        # Simple keyword extraction
        words = re.findall(r'\b\w{3,}\b', text.lower())
        
        # Filter out common words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 
            'did', 'what', 'when', 'where', 'why', 'will', 'with', 'have', 'this',
            'that', 'they', 'them', 'been', 'said', 'each', 'which', 'their'
        }
        
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        return keywords[:5]  # Return top 5 keywords
    
    async def store_conversation(
        self, 
        user_message: str, 
        agent_response: str,
        chat_id: Optional[str] = None
    ):
        """Store conversation in fast chat storage"""
        await self.fast_chat.store_message(user_message, "user", chat_id)
        await self.fast_chat.store_message(agent_response, "assistant", chat_id)

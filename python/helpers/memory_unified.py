"""
Unified Memory System for Agent Zero
Supports both FAISS and MongoDB Atlas Vector Search with user isolation
"""

import uuid
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
from langchain_core.documents import Document

from agent import Agent
from python.helpers.vector_store import VectorStore, VectorStoreFactory, get_default_provider
from python.helpers.print_style import PrintStyle
from python.helpers import files
from python.helpers.log import LogItem
from models import vector_store_config


class MemoryArea(Enum):
    MAIN = "main"
    FRAGMENTS = "fragments"
    SOLUTIONS = "solutions"
    INSTRUMENTS = "instruments"


class UnifiedMemory:
    """Unified memory system with vector store abstraction"""
    
    # Class-level cache for vector stores
    _vector_stores: Dict[str, VectorStore] = {}
    
    def __init__(
        self,
        agent: Agent,
        vector_store: VectorStore,
        user_id: Optional[str] = None,
        memory_subdir: str = "default"
    ):
        self.agent = agent
        self.vector_store = vector_store
        self.user_id = user_id
        self.memory_subdir = memory_subdir
    
    @classmethod
    async def get(cls, agent: Agent, user_id: Optional[str] = None) -> 'UnifiedMemory':
        """Get or create memory instance for user"""
        memory_subdir = agent.config.memory_subdir or "default"
        
        # Create cache key
        cache_key = f"{user_id or 'default'}_{memory_subdir}"
        
        # Check if already cached
        if cache_key in cls._vector_stores:
            return cls(
                agent=agent,
                vector_store=cls._vector_stores[cache_key],
                user_id=user_id,
                memory_subdir=memory_subdir
            )
        
        # Create new vector store
        log_item = agent.context.log.log(
            type="util",
            heading=f"Initializing Vector Store for user: {user_id or 'default'}"
        )
        
        vector_store = await cls._create_vector_store(
            agent=agent,
            user_id=user_id,
            memory_subdir=memory_subdir,
            log_item=log_item
        )
        
        if not vector_store:
            raise Exception("Failed to create vector store")
        
        # Cache the vector store
        cls._vector_stores[cache_key] = vector_store
        
        # Create memory instance
        memory = cls(
            agent=agent,
            vector_store=vector_store,
            user_id=user_id,
            memory_subdir=memory_subdir
        )
        
        # Preload knowledge if configured
        if agent.config.knowledge_subdirs:
            await memory.preload_knowledge(log_item, agent.config.knowledge_subdirs)
        
        return memory
    
    @classmethod
    async def _create_vector_store(
        cls,
        agent: Agent,
        user_id: Optional[str],
        memory_subdir: str,
        log_item: Optional[LogItem] = None
    ) -> Optional[VectorStore]:
        """Create vector store instance"""
        try:
            if log_item:
                log_item.stream(progress=f"\nInitializing {vector_store_config.provider} vector store")
            
            PrintStyle.standard(f"Creating {vector_store_config.provider} vector store...")
            
            # Get embeddings model
            embeddings_model = agent.get_embedding_model()
            
            # Determine provider
            if vector_store_config.use_mongodb:
                provider = VectorStoreFactory.get_provider_from_string("mongodb")
                PrintStyle.success("Using MongoDB Atlas Vector Search")
            else:
                provider = VectorStoreFactory.get_provider_from_string("faiss")
                PrintStyle.success("Using FAISS Vector Store")
            
            # Create vector store
            vector_store = VectorStoreFactory.create_vector_store(
                provider=provider,
                embeddings=embeddings_model,
                user_id=user_id,
                memory_subdir=memory_subdir
            )
            
            if log_item:
                log_item.stream(progress=f"\n✓ Vector store initialized")
            
            return vector_store
            
        except Exception as e:
            PrintStyle.error(f"Failed to create vector store: {str(e)}")
            if log_item:
                log_item.stream(progress=f"\n✗ Vector store initialization failed: {str(e)}")
            return None
    
    @classmethod
    async def reload(cls, agent: Agent, user_id: Optional[str] = None) -> 'UnifiedMemory':
        """Reload memory (clear cache and recreate)"""
        memory_subdir = agent.config.memory_subdir or "default"
        cache_key = f"{user_id or 'default'}_{memory_subdir}"
        
        # Remove from cache
        if cache_key in cls._vector_stores:
            del cls._vector_stores[cache_key]
        
        # Create new instance
        return await cls.get(agent, user_id)
    
    async def search_similarity_threshold(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.1,
        area: Optional[MemoryArea] = None
    ) -> List[Document]:
        """Search for similar memories with threshold"""
        try:
            # Build filter
            filter_dict = {}
            if area:
                filter_dict["area"] = area.value
            
            # Rate limiting
            await self.agent.rate_limiter(
                model_config=self.agent.config.embeddings_model,
                input=query
            )
            
            # Search
            results = await self.vector_store.asimilarity_search_with_score(
                query=query,
                k=limit,
                filter=filter_dict,
                score_threshold=threshold
            )
            
            # Extract documents
            documents = [doc for doc, score in results]
            
            PrintStyle.success(f"Found {len(documents)} similar memories")
            return documents
            
        except Exception as e:
            PrintStyle.error(f"Memory search failed: {str(e)}")
            return []
    
    async def insert_documents(self, docs: List[Document]) -> List[str]:
        """Insert documents into memory"""
        try:
            # Add metadata
            timestamp = datetime.utcnow().isoformat()
            
            for doc in docs:
                if "id" not in doc.metadata:
                    doc.metadata["id"] = str(uuid.uuid4())
                doc.metadata["timestamp"] = timestamp
                if "area" not in doc.metadata:
                    doc.metadata["area"] = MemoryArea.MAIN.value
                if self.user_id:
                    doc.metadata["user_id"] = self.user_id
            
            # Rate limiting
            docs_txt = "".join([doc.page_content for doc in docs])
            await self.agent.rate_limiter(
                model_config=self.agent.config.embeddings_model,
                input=docs_txt
            )
            
            # Insert documents
            ids = await self.vector_store.aadd_documents(
                documents=docs,
                ids=[doc.metadata["id"] for doc in docs]
            )
            
            PrintStyle.success(f"Inserted {len(docs)} documents into memory")
            return ids
            
        except Exception as e:
            PrintStyle.error(f"Failed to insert documents: {str(e)}")
            return []
    
    async def delete_documents(self, ids: List[str]) -> bool:
        """Delete documents from memory"""
        try:
            success = await self.vector_store.adelete(ids)
            if success:
                PrintStyle.success(f"Deleted {len(ids)} documents from memory")
            return success
            
        except Exception as e:
            PrintStyle.error(f"Failed to delete documents: {str(e)}")
            return False
    
    async def preload_knowledge(
        self,
        log_item: Optional[LogItem],
        knowledge_subdirs: List[str]
    ):
        """Preload knowledge from directories"""
        try:
            if log_item:
                log_item.stream(progress="\nPreloading knowledge...")
            
            PrintStyle.standard("Preloading knowledge base...")
            
            for subdir in knowledge_subdirs:
                await self._load_knowledge_from_dir(subdir, log_item)
            
            PrintStyle.success("Knowledge preloading completed")
            
        except Exception as e:
            PrintStyle.error(f"Knowledge preloading failed: {str(e)}")
    
    async def _load_knowledge_from_dir(
        self,
        knowledge_subdir: str,
        log_item: Optional[LogItem]
    ):
        """Load knowledge from a specific directory"""
        try:
            knowledge_path = files.get_abs_path("knowledge", knowledge_subdir)
            
            if not files.exists(knowledge_path):
                PrintStyle.warning(f"Knowledge directory not found: {knowledge_path}")
                return
            
            # Get all files in directory
            files_list = files.get_files_in_dir(knowledge_path, recursive=True)
            
            for file_path in files_list:
                if file_path.endswith(('.txt', '.md', '.json')):
                    await self._load_knowledge_file(file_path, knowledge_subdir, log_item)
            
        except Exception as e:
            PrintStyle.error(f"Failed to load knowledge from {knowledge_subdir}: {str(e)}")
    
    async def _load_knowledge_file(
        self,
        file_path: str,
        knowledge_subdir: str,
        log_item: Optional[LogItem]
    ):
        """Load a single knowledge file"""
        try:
            content = files.read_file(file_path)
            if not content.strip():
                return
            
            # Create document
            doc = Document(
                page_content=content,
                metadata={
                    "source": file_path,
                    "knowledge_subdir": knowledge_subdir,
                    "area": MemoryArea.MAIN.value,
                    "type": "knowledge"
                }
            )
            
            # Insert document
            await self.insert_documents([doc])
            
            if log_item:
                log_item.stream(progress=f"\n  ✓ Loaded: {file_path}")
            
        except Exception as e:
            PrintStyle.error(f"Failed to load knowledge file {file_path}: {str(e)}")
    
    def get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.utcnow().isoformat()
    
    def format_docs_plain(self, docs: List[Document]) -> List[str]:
        """Format documents as plain text"""
        result = []
        for doc in docs:
            text = ""
            for k, v in doc.metadata.items():
                text += f"{k}: {v}\n"
            text += f"Content: {doc.page_content}"
            result.append(text)
        return result

"""
MongoDB Atlas Vector Search implementation for Agent Zero
Multi-tenant vector store with user isolation
"""

import uuid
from typing import List, Optional, Dict, Any, Tuple
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_mongodb.vectorstores import MongoDBAtlasVectorSearch

from python.helpers.vector_store import VectorStore
from python.helpers.mongodb_client import get_mongodb_client
from python.helpers.print_style import PrintStyle
from python.helpers.dotenv import get_dotenv_value


class MongoDBVectorStore(VectorStore):
    """MongoDB Atlas Vector Search implementation with multi-tenant support"""
    
    def __init__(
        self,
        embeddings: Embeddings,
        user_id: Optional[str] = None,
        collection_name: Optional[str] = None,
        index_name: str = "vector_search_index",
        **kwargs  # Accept any additional arguments for compatibility
    ):
        super().__init__(user_id)
        self.embeddings = embeddings
        self.collection_name = collection_name or get_dotenv_value("MONGODB_COLLECTION_MEMORY") or "user_memory"
        self.index_name = index_name
        self.vector_search: Optional[MongoDBAtlasVectorSearch] = None
        self._initialized = False
    
    async def _ensure_initialized(self) -> bool:
        """Ensure MongoDB connection and vector search are initialized"""
        if self._initialized and self.vector_search:
            return True
        
        try:
            # Get MongoDB client
            mongodb_client = await get_mongodb_client()
            if not await mongodb_client.ensure_connected():
                PrintStyle.error("Failed to connect to MongoDB Atlas")
                return False
            
            # Get collection
            collection = mongodb_client.get_collection(self.collection_name)
            if not collection:
                PrintStyle.error(f"Failed to get collection: {self.collection_name}")
                return False
            
            # Initialize vector search
            self.vector_search = MongoDBAtlasVectorSearch(
                collection=collection,
                embedding=self.embeddings,
                index_name=self.index_name,
                text_key="content",
                embedding_key="embedding"
            )
            
            self._initialized = True
            PrintStyle.success(f"MongoDB Vector Search initialized for collection: {self.collection_name}")
            return True
            
        except Exception as e:
            PrintStyle.error(f"Failed to initialize MongoDB Vector Search: {str(e)}")
            return False
    
    def _get_user_filter(self, additional_filter: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get filter with user isolation"""
        user_filter = {}
        
        if self.user_id:
            user_filter["user_id"] = {"$eq": self.user_id}
        
        if additional_filter:
            user_filter.update(additional_filter)
        
        return user_filter
    
    async def asimilarity_search_with_score(
        self, 
        query: str, 
        k: int = 5, 
        filter: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[Document, float]]:
        """Search for similar documents with scores"""
        if not await self._ensure_initialized():
            return []
        
        try:
            # Apply user filter
            combined_filter = self._get_user_filter(filter)
            
            # Perform vector search
            if score_threshold is not None:
                results = await self.vector_search.asimilarity_search_with_score(
                    query=query,
                    k=k,
                    filter=combined_filter,
                    score_threshold=score_threshold
                )
            else:
                results = await self.vector_search.asimilarity_search_with_score(
                    query=query,
                    k=k,
                    filter=combined_filter
                )
            
            return results
            
        except Exception as e:
            PrintStyle.error(f"MongoDB vector search failed: {str(e)}")
            return []
    
    async def aadd_documents(
        self, 
        documents: List[Document], 
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add documents to the vector store"""
        if not await self._ensure_initialized():
            return []
        
        try:
            if not ids:
                ids = [str(uuid.uuid4()) for _ in documents]
            
            # Add user_id and metadata to all documents
            for i, doc in enumerate(documents):
                if self.user_id:
                    doc.metadata["user_id"] = self.user_id
                doc.metadata["_id"] = ids[i]
                
                # Ensure required fields
                if "timestamp" not in doc.metadata:
                    from datetime import datetime
                    doc.metadata["timestamp"] = datetime.utcnow()
            
            # Add documents to MongoDB
            await self.vector_search.aadd_documents(documents=documents, ids=ids)
            
            PrintStyle.success(f"Added {len(documents)} documents to MongoDB")
            return ids
            
        except Exception as e:
            PrintStyle.error(f"Failed to add documents to MongoDB: {str(e)}")
            return []
    
    async def adelete(self, ids: List[str]) -> bool:
        """Delete documents by IDs"""
        if not await self._ensure_initialized():
            return False
        
        try:
            mongodb_client = await get_mongodb_client()
            collection = mongodb_client.get_collection(self.collection_name)
            
            if not collection:
                return False
            
            # Build delete filter with user isolation
            delete_filter = {"_id": {"$in": ids}}
            if self.user_id:
                delete_filter["user_id"] = self.user_id
            
            # Delete documents
            result = await collection.delete_many(delete_filter)
            
            PrintStyle.success(f"Deleted {result.deleted_count} documents from MongoDB")
            return result.deleted_count > 0
            
        except Exception as e:
            PrintStyle.error(f"Failed to delete documents from MongoDB: {str(e)}")
            return False
    
    def get_all_docs(self) -> Dict[str, Document]:
        """Get all documents (for FAISS compatibility)"""
        # This is a synchronous method for FAISS compatibility
        # In practice, this should be avoided for large datasets
        PrintStyle.warning("get_all_docs() is not recommended for MongoDB - use async search instead")
        return {}
    
    async def aget_all_docs(self) -> List[Document]:
        """Get all documents for the current user (async version)"""
        if not await self._ensure_initialized():
            return []
        
        try:
            mongodb_client = await get_mongodb_client()
            collection = mongodb_client.get_collection(self.collection_name)
            
            if not collection:
                return []
            
            # Build filter with user isolation
            filter_query = self._get_user_filter()
            
            # Get all documents
            cursor = collection.find(filter_query)
            documents = []
            
            async for doc in cursor:
                # Convert MongoDB document to LangChain Document
                content = doc.get("content", "")
                metadata = {k: v for k, v in doc.items() if k not in ["content", "embedding"]}
                documents.append(Document(page_content=content, metadata=metadata))
            
            return documents
            
        except Exception as e:
            PrintStyle.error(f"Failed to get all documents from MongoDB: {str(e)}")
            return []
    
    async def asearch(
        self,
        query: str,
        search_type: str = "similarity",
        k: int = 5,
        score_threshold: Optional[float] = None,
        filter: Optional[Any] = None,
        **kwargs
    ) -> List[Document]:
        """Generic search method for compatibility"""
        if not await self._ensure_initialized():
            return []
        
        try:
            # Apply user filter
            combined_filter = self._get_user_filter(filter)
            
            if search_type == "similarity_score_threshold" and score_threshold:
                results = await self.vector_search.asimilarity_search(
                    query=query,
                    k=k,
                    filter=combined_filter,
                    score_threshold=score_threshold,
                    **kwargs
                )
            else:
                results = await self.vector_search.asimilarity_search(
                    query=query,
                    k=k,
                    filter=combined_filter,
                    **kwargs
                )
            
            return results
            
        except Exception as e:
            PrintStyle.error(f"MongoDB search failed: {str(e)}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            mongodb_client = await get_mongodb_client()
            stats = await mongodb_client.get_collection_stats(self.collection_name)
            
            if stats and self.user_id:
                # Get user-specific count
                collection = mongodb_client.get_collection(self.collection_name)
                if collection:
                    user_count = await collection.count_documents({"user_id": self.user_id})
                    stats["user_document_count"] = user_count
            
            return stats or {}
            
        except Exception as e:
            PrintStyle.error(f"Failed to get MongoDB stats: {str(e)}")
            return {}

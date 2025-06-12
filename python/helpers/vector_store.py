"""
Unified Vector Store abstraction for Agent Zero
Supports both FAISS (local) and MongoDB Atlas Vector Search
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from enum import Enum


class VectorStoreProvider(Enum):
    FAISS = "faiss"
    MONGODB = "mongodb"


class VectorStore(ABC):
    """Abstract base class for vector stores"""
    
    def __init__(self, user_id: Optional[str] = None):
        self.user_id = user_id
    
    @abstractmethod
    async def asimilarity_search_with_score(
        self, 
        query: str, 
        k: int = 5, 
        filter: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[Document, float]]:
        """Search for similar documents with scores"""
        pass
    
    @abstractmethod
    async def aadd_documents(
        self, 
        documents: List[Document], 
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add documents to the vector store"""
        pass
    
    @abstractmethod
    async def adelete(self, ids: List[str]) -> bool:
        """Delete documents by IDs"""
        pass
    
    @abstractmethod
    def get_all_docs(self) -> Dict[str, Document]:
        """Get all documents (for FAISS compatibility)"""
        pass
    
    @abstractmethod
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
        pass


class VectorStoreFactory:
    """Factory for creating vector store instances"""
    
    @staticmethod
    def create_vector_store(
        provider: VectorStoreProvider,
        embeddings: Embeddings,
        user_id: Optional[str] = None,
        **kwargs
    ) -> VectorStore:
        """Create a vector store instance"""
        
        if provider == VectorStoreProvider.FAISS:
            from python.helpers.vector_store_faiss import FAISSVectorStore
            return FAISSVectorStore(embeddings=embeddings, user_id=user_id, **kwargs)
        
        elif provider == VectorStoreProvider.MONGODB:
            from python.helpers.vector_store_mongodb import MongoDBVectorStore
            return MongoDBVectorStore(embeddings=embeddings, user_id=user_id, **kwargs)
        
        else:
            raise ValueError(f"Unsupported vector store provider: {provider}")
    
    @staticmethod
    def get_provider_from_string(provider_str: str) -> VectorStoreProvider:
        """Convert string to VectorStoreProvider enum"""
        provider_str = provider_str.lower()
        
        if provider_str in ["faiss", "local"]:
            return VectorStoreProvider.FAISS
        elif provider_str in ["mongodb", "mongo", "atlas"]:
            return VectorStoreProvider.MONGODB
        else:
            raise ValueError(f"Unknown vector store provider: {provider_str}")


# Utility functions for backward compatibility
async def create_vector_store(
    provider: str,
    embeddings: Embeddings,
    user_id: Optional[str] = None,
    **kwargs
) -> VectorStore:
    """Create vector store with string provider"""
    provider_enum = VectorStoreFactory.get_provider_from_string(provider)
    return VectorStoreFactory.create_vector_store(
        provider=provider_enum,
        embeddings=embeddings,
        user_id=user_id,
        **kwargs
    )


def get_default_provider() -> VectorStoreProvider:
    """Get the default vector store provider from environment"""
    from python.helpers.dotenv import get_dotenv_value
    
    provider_str = get_dotenv_value("VECTOR_STORE_PROVIDER") or "faiss"
    
    try:
        return VectorStoreFactory.get_provider_from_string(provider_str)
    except ValueError:
        # Default to FAISS if invalid provider
        return VectorStoreProvider.FAISS

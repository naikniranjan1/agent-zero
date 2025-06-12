"""
FAISS Vector Store implementation for Agent Zero
Wraps existing FAISS functionality with the new VectorStore interface
"""

import os
import json
import uuid
from typing import List, Optional, Dict, Any, Tuple, Sequence
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain.storage import LocalFileStore, InMemoryByteStore
from langchain.embeddings import CacheBackedEmbeddings
import faiss

from python.helpers.vector_store import VectorStore
from python.helpers import files
from python.helpers.print_style import PrintStyle


class MyFaiss(FAISS):
    """Extended FAISS with additional methods"""
    
    def get_by_ids(self, ids: Sequence[str], /) -> List[Document]:
        return [self.docstore._dict[id] for id in (ids if isinstance(ids, list) else [ids]) if id in self.docstore._dict]  # type: ignore

    async def aget_by_ids(self, ids: Sequence[str], /) -> List[Document]:
        return self.get_by_ids(ids)

    def get_all_docs(self):
        return self.docstore._dict  # type: ignore


class FAISSVectorStore(VectorStore):
    """FAISS implementation of VectorStore interface"""
    
    def __init__(
        self, 
        embeddings: Embeddings,
        user_id: Optional[str] = None,
        memory_subdir: str = "default",
        in_memory: bool = False
    ):
        super().__init__(user_id)
        self.embeddings = embeddings
        self.memory_subdir = memory_subdir
        self.in_memory = in_memory
        self.db: Optional[MyFaiss] = None
        
        # Initialize FAISS database
        self._initialize_faiss()
    
    def _initialize_faiss(self):
        """Initialize FAISS database"""
        try:
            PrintStyle.standard("Initializing FAISS VectorDB...")
            
            # Setup directories
            em_dir = files.get_abs_path("memory/embeddings")
            db_dir = self._get_db_dir()
            
            os.makedirs(db_dir, exist_ok=True)
            
            # Setup embedding cache
            if self.in_memory:
                store = InMemoryByteStore()
            else:
                os.makedirs(em_dir, exist_ok=True)
                store = LocalFileStore(em_dir)
            
            # Create cached embeddings
            embeddings_model_id = files.safe_file_name(
                getattr(self.embeddings, 'model', 'default') or 'default'
            )
            
            self.cached_embeddings = CacheBackedEmbeddings.from_bytes_store(
                self.embeddings, store, namespace=embeddings_model_id
            )
            
            # Load or create FAISS index
            if os.path.exists(db_dir) and files.exists(db_dir, "index.faiss"):
                self._load_existing_db(db_dir)
            else:
                self._create_new_db()
                
            PrintStyle.success("FAISS VectorDB initialized")
            
        except Exception as e:
            PrintStyle.error(f"Failed to initialize FAISS: {str(e)}")
            raise
    
    def _get_db_dir(self) -> str:
        """Get database directory path"""
        if self.user_id:
            # User-specific directory
            return files.get_abs_path(f"memory/{self.user_id}/{self.memory_subdir}")
        else:
            # Legacy directory structure
            return files.get_abs_path(f"memory/{self.memory_subdir}")
    
    def _load_existing_db(self, db_dir: str):
        """Load existing FAISS database"""
        try:
            self.db = MyFaiss.load_local(
                folder_path=db_dir,
                embeddings=self.cached_embeddings,
                allow_dangerous_deserialization=True,
                distance_strategy=DistanceStrategy.COSINE,
                relevance_score_fn=self._cosine_normalizer,
            )
            PrintStyle.success(f"Loaded existing FAISS database from {db_dir}")
            
        except Exception as e:
            PrintStyle.warning(f"Failed to load existing database: {str(e)}")
            self._create_new_db()
    
    def _create_new_db(self):
        """Create new FAISS database"""
        try:
            # Create FAISS index
            dimension = len(self.cached_embeddings.embed_query("example"))
            index = faiss.IndexFlatIP(dimension)
            
            self.db = MyFaiss(
                embedding_function=self.cached_embeddings,
                index=index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
                distance_strategy=DistanceStrategy.COSINE,
                relevance_score_fn=self._cosine_normalizer,
            )
            
            # Save the new database
            self._save_db()
            PrintStyle.success("Created new FAISS database")
            
        except Exception as e:
            PrintStyle.error(f"Failed to create FAISS database: {str(e)}")
            raise
    
    def _save_db(self):
        """Save FAISS database to disk"""
        if self.db and not self.in_memory:
            try:
                db_dir = self._get_db_dir()
                os.makedirs(db_dir, exist_ok=True)
                self.db.save_local(db_dir)
                
                # Save metadata
                meta_file = os.path.join(db_dir, "embedding.json")
                metadata = {
                    "model_provider": getattr(self.embeddings, 'model', 'default'),
                    "model_name": getattr(self.embeddings, 'model', 'default'),
                    "user_id": self.user_id
                }
                with open(meta_file, 'w') as f:
                    json.dump(metadata, f)
                    
            except Exception as e:
                PrintStyle.error(f"Failed to save FAISS database: {str(e)}")
    
    @staticmethod
    def _cosine_normalizer(val: float) -> float:
        """Normalize cosine similarity score"""
        return (val + 1) / 2
    
    async def asimilarity_search_with_score(
        self, 
        query: str, 
        k: int = 5, 
        filter: Optional[Dict[str, Any]] = None,
        score_threshold: Optional[float] = None
    ) -> List[Tuple[Document, float]]:
        """Search for similar documents with scores"""
        if not self.db:
            return []
        
        try:
            if score_threshold is not None:
                results = await self.db.asimilarity_search_with_score(
                    query, k=k, score_threshold=score_threshold, filter=filter
                )
            else:
                results = await self.db.asimilarity_search_with_score(
                    query, k=k, filter=filter
                )
            return results
            
        except Exception as e:
            PrintStyle.error(f"FAISS search failed: {str(e)}")
            return []
    
    async def aadd_documents(
        self, 
        documents: List[Document], 
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add documents to the vector store"""
        if not self.db:
            return []
        
        try:
            if not ids:
                ids = [str(uuid.uuid4()) for _ in documents]
            
            # Add user_id to metadata if provided
            if self.user_id:
                for doc in documents:
                    doc.metadata["user_id"] = self.user_id
            
            await self.db.aadd_documents(documents=documents, ids=ids)
            self._save_db()
            return ids
            
        except Exception as e:
            PrintStyle.error(f"Failed to add documents to FAISS: {str(e)}")
            return []
    
    async def adelete(self, ids: List[str]) -> bool:
        """Delete documents by IDs"""
        if not self.db:
            return False
        
        try:
            # FAISS doesn't have native delete, so we need to rebuild
            # This is a limitation of FAISS
            PrintStyle.warning("FAISS delete operation requires rebuilding index")
            return False
            
        except Exception as e:
            PrintStyle.error(f"Failed to delete from FAISS: {str(e)}")
            return False
    
    def get_all_docs(self) -> Dict[str, Document]:
        """Get all documents"""
        if not self.db:
            return {}
        return self.db.get_all_docs()
    
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
        if not self.db:
            return []
        
        try:
            if search_type == "similarity_score_threshold" and score_threshold:
                return await self.db.asearch(
                    query,
                    search_type=search_type,
                    k=k,
                    score_threshold=score_threshold,
                    filter=filter,
                    **kwargs
                )
            else:
                return await self.db.asearch(
                    query,
                    search_type=search_type,
                    k=k,
                    filter=filter,
                    **kwargs
                )
                
        except Exception as e:
            PrintStyle.error(f"FAISS search failed: {str(e)}")
            return []

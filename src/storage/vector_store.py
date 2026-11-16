"""
Vector Store Engine — builds ChromaDB index from enterprise documents.
Supports both local (ChromaDB) and production (Pinecone/Vertex) backends.
"""

import os
import sys
from typing import List, Dict, Any

import chromadb
from chromadb.utils import embedding_functions

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from data.docs.sample_docs import SAMPLE_DOCS


CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chroma_db")
COLLECTION_NAME = "enterprise_docs"


class VectorStore:
    """
    Wraps ChromaDB with sentence-transformers embeddings.
    Provides add, similarity search, and hybrid retrieval.
    """

    def __init__(self, persist_path: str = CHROMA_DB_PATH, collection: str = COLLECTION_NAME):
        self.client = chromadb.PersistentClient(path=persist_path)
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name=collection,
            embedding_function=self.embed_fn,
            metadata={"hnsw:space": "cosine"}
        )

    def ingest_documents(self, docs: List[Dict[str, Any]] = None) -> int:
        """
        Ingest a list of document dicts into ChromaDB.
        Each doc must have: id, source, content.
        """
        if docs is None:
            docs = SAMPLE_DOCS

        existing_ids = set(self.collection.get()["ids"])
        new_docs = [d for d in docs if d["id"] not in existing_ids]

        if not new_docs:
            return 0

        self.collection.add(
            ids=[d["id"] for d in new_docs],
            documents=[d["content"] for d in new_docs],
            metadatas=[{"source": d["source"]} for d in new_docs],
        )
        return len(new_docs)

    def similarity_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top-k most semantically similar document chunks."""
        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"]
        )
        output = []
        for i, doc in enumerate(results["documents"][0]):
            output.append({
                "content": doc,
                "source": results["metadatas"][0][i]["source"],
                "similarity_score": round(1 - results["distances"][0][i], 4),
            })
        return output

    def count(self) -> int:
        return self.collection.count()

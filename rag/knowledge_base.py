import hashlib
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

from config import CHROMA_DB_PATH


class KnowledgeBase:
    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=str(CHROMA_DB_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collections = {}

    def _get_collection_name(self, project_path: str) -> str:
        return "proj_" + hashlib.md5(project_path.encode()).hexdigest()[:12]

    def get_collection(self, project_path: str):
        name = self._get_collection_name(project_path)
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                metadata={"project_path": project_path},
            )
        return self._collections[name]

    def store(
        self,
        project_path: str,
        content: str,
        metadata: dict,
        doc_id: Optional[str] = None,
        embedding: Optional[list[float]] = None,
    ):
        collection = self.get_collection(project_path)
        if doc_id is None:
            doc_id = hashlib.md5(content.encode()).hexdigest()
        kwargs = {"ids": [doc_id], "documents": [content], "metadatas": [metadata]}
        if embedding is not None:
            kwargs["embeddings"] = [embedding]
        collection.upsert(**kwargs)

    def query(
        self,
        project_path: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[dict] = None,
        query_embedding: Optional[list[float]] = None,
    ) -> list[dict]:
        collection = self.get_collection(project_path)
        kwargs = {"n_results": n_results}
        if where:
            kwargs["where"] = where
        if query_embedding is not None:
            kwargs["query_embeddings"] = [query_embedding]
        else:
            kwargs["query_texts"] = [query_text]
        results = collection.query(**kwargs)
        items = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                item = {"content": doc}
                if results["metadatas"] and results["metadatas"][0]:
                    item["metadata"] = results["metadatas"][0][i]
                if results["distances"] and results["distances"][0]:
                    item["distance"] = results["distances"][0][i]
                items.append(item)
        return items

    def list_projects(self) -> list[str]:
        return [c.name for c in self._client.list_collections()]

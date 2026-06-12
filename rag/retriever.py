from typing import Optional

from rag.knowledge_base import KnowledgeBase
from rag.embedder import Embedder


class Retriever:
    def __init__(self, kb: KnowledgeBase, embedder: Embedder):
        self._kb = kb
        self._embedder = embedder

    def retrieve(
        self,
        project_path: str,
        query: str,
        n_results: int = 5,
        doc_type: Optional[str] = None,
    ) -> list[dict]:
        query_embedding = self._embedder.embed(query)
        where = {"type": doc_type} if doc_type else None
        return self._kb.query(
            project_path=project_path,
            query_text=query,
            n_results=n_results,
            where=where,
            query_embedding=query_embedding,
        )

    def store_decision(
        self,
        project_path: str,
        content: str,
        agent_role: str,
        doc_type: str = "decision",
        file_path: Optional[str] = None,
    ):
        embedding = self._embedder.embed(content)
        metadata = {
            "type": doc_type,
            "agent": agent_role,
        }
        if file_path:
            metadata["file"] = file_path
        self._kb.store(
            project_path=project_path,
            content=content,
            metadata=metadata,
            embedding=embedding,
        )

    def store_bug(
        self,
        project_path: str,
        description: str,
        solution: str,
        agent_role: str,
        file_path: Optional[str] = None,
    ):
        content = f"Bug: {description}\nSolution: {solution}"
        self.store_decision(
            project_path=project_path,
            content=content,
            agent_role=agent_role,
            doc_type="bug",
            file_path=file_path,
        )

    def store_pattern(
        self,
        project_path: str,
        pattern: str,
        agent_role: str,
        file_path: Optional[str] = None,
    ):
        self.store_decision(
            project_path=project_path,
            content=pattern,
            agent_role=agent_role,
            doc_type="pattern",
            file_path=file_path,
        )

    def get_context(self, project_path: str, query: str, n_results: int = 10) -> str:
        results = self.retrieve(project_path, query, n_results)
        if not results:
            return ""
        parts = []
        for r in results:
            meta = r.get("metadata", {})
            agent = meta.get("agent", "unknown")
            doc_type = meta.get("type", "unknown")
            parts.append(f"[{doc_type} by {agent}]\n{r['content']}")
        return "\n\n---\n\n".join(parts)

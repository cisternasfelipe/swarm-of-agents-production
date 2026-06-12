from typing import Optional

from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL


class Embedder:
    _instance: Optional["Embedder"] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_model(self):
        if self._model is None:
            self._model = SentenceTransformer(EMBEDDING_MODEL)

    def embed(self, text: str) -> list[float]:
        self._ensure_model()
        return self._model.encode(text).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._ensure_model()
        return [e.tolist() for e in self._model.encode(texts)]

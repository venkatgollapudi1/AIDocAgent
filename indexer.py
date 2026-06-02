"""
Document indexer: chunks pages, builds a BM25 search index,
and persists everything to disk for fast reuse.
"""

import json
import math
import os
import pickle
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Optional

from .config import Config


@dataclass
class Chunk:
    doc_id: str
    chunk_id: int
    title: str
    url: str
    breadcrumb: str
    labels: list[str]
    text: str
    tokens: list[str] = field(default_factory=list, repr=False)


class BM25Index:
    """Minimal BM25 implementation — no external dependencies required."""

    K1 = 1.5
    B = 0.75

    def __init__(self):
        self.chunks: list[Chunk] = []
        self.df: dict[str, int] = defaultdict(int)  # document frequency
        self.avgdl: float = 0.0

    def add_chunks(self, chunks: list[Chunk]):
        self.chunks = chunks
        total_len = 0
        for chunk in chunks:
            chunk.tokens = self._tokenize(chunk.text + " " + chunk.title)
            total_len += len(chunk.tokens)
            for term in set(chunk.tokens):
                self.df[term] += 1
        self.avgdl = total_len / max(len(chunks), 1)

    def search(self, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        query_tokens = self._tokenize(query)
        n = len(self.chunks)
        scores = []

        for chunk in self.chunks:
            tf_map = Counter(chunk.tokens)
            dl = len(chunk.tokens)
            score = 0.0
            for term in query_tokens:
                if term not in tf_map:
                    continue
                tf = tf_map[term]
                df = self.df.get(term, 0)
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (tf * (self.K1 + 1)) / (
                    tf + self.K1 * (1 - self.B + self.B * dl / self.avgdl)
                )
                score += idf * tf_norm
            scores.append((chunk, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [(c, s) for c, s in scores[:top_k] if s > 0]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        text = text.lower()
        tokens = re.findall(r"[a-z0-9]+", text)
        # Simple stop word removal
        stop_words = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "was", "are", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "can", "this",
            "that", "these", "those", "it", "its", "as", "not",
        }
        return [t for t in tokens if t not in stop_words and len(t) > 1]


class DocumentIndexer:
    def __init__(self, config: Config):
        self.config = config
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.index_dir = config.index_dir
        os.makedirs(self.index_dir, exist_ok=True)

    def _index_path(self, space_key: str) -> str:
        return os.path.join(self.index_dir, f"{space_key}.pkl")

    def _meta_path(self, space_key: str) -> str:
        return os.path.join(self.index_dir, f"{space_key}_meta.json")

    def index_exists(self, space_key: str) -> bool:
        return os.path.exists(self._index_path(space_key))

    def get_index_count(self, space_key: str) -> int:
        if not os.path.exists(self._meta_path(space_key)):
            return 0
        with open(self._meta_path(space_key)) as f:
            meta = json.load(f)
        return meta.get("chunk_count", 0)

    def index_pages(self, space_key: str, pages: list[dict]):
        """Chunk all pages and build the BM25 index."""
        chunks = []
        for page in pages:
            page_chunks = self._chunk_page(page)
            chunks.extend(page_chunks)

        index = BM25Index()
        index.add_chunks(chunks)

        with open(self._index_path(space_key), "wb") as f:
            pickle.dump(index, f)

        with open(self._meta_path(space_key), "w") as f:
            json.dump({"chunk_count": len(chunks), "page_count": len(pages)}, f)

    def load_index(self, space_key: str) -> Optional[BM25Index]:
        path = self._index_path(space_key)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return pickle.load(f)

    def search(self, space_key: str, query: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        index = self.load_index(space_key)
        if not index:
            return []
        return index.search(query, top_k=top_k)

    def _chunk_page(self, page: dict) -> list[Chunk]:
        """Split page text into overlapping chunks."""
        text = page["text"]
        if not text.strip():
            return []

        size = self.chunk_size
        overlap = self.chunk_overlap
        words = text.split()
        chunks = []
        start = 0
        chunk_id = 0

        while start < len(words):
            end = min(start + size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(
                Chunk(
                    doc_id=page["id"],
                    chunk_id=chunk_id,
                    title=page["title"],
                    url=page["url"],
                    breadcrumb=page["breadcrumb"],
                    labels=page["labels"],
                    text=chunk_text,
                )
            )
            chunk_id += 1
            if end == len(words):
                break
            start += size - overlap

        return chunks

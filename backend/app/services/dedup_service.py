import re
import math
import hashlib
from typing import List, Tuple, Optional

class DeduplicationService:
    """Implements 2-Pass Deduplication for opportunity crawling."""

    @staticmethod
    def compute_sha256_fingerprint(canonical_url: str, title: str) -> str:
        """Pass 1: Computes cryptographic fingerprint."""
        normalized_url = re.sub(r"^https?://(www\.)?", "", canonical_url.strip().lower()).rstrip("/")
        normalized_title = title.strip().lower()
        combined = f"{normalized_url}::{normalized_title}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Computes cosine similarity between two vector lists."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    def is_semantic_duplicate(
        self,
        candidate_embedding: List[float],
        existing_embeddings: List[Tuple[str, List[float]]],
        threshold: float = 0.88
    ) -> Optional[str]:
        """
        Pass 2: Checks if candidate embedding exceeds cosine threshold (0.88)
        against existing opportunity embeddings.
        Returns the matching ID if duplicate found, else None.
        """
        for opp_id, emb in existing_embeddings:
            sim = self.cosine_similarity(candidate_embedding, emb)
            if sim >= threshold:
                return opp_id
        return None

dedup_service = DeduplicationService()


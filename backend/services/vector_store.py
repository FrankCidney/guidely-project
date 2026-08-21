import os
from typing import List, Tuple, Optional
import faiss
import numpy as np
from pathlib import Path
from backend.config import FAISS_INDEX_PATH

class FAISSManager:
    """
    Manages the FAISS vector index.
    """

    def __init__(self, index_path: Optional[str] = None, dimension: int = 768):
        self.index_path = index_path or FAISS_INDEX_PATH
        self.dimension = dimension

        # Load existing index from disk if available, otherwise create a new empty index
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)

    def save(self):
        """Saves the FAISS index binary to disk."""
        index_dir = Path(self.index_path).parent
        index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, self.index_path)

    def add_vectors(self, vectors: List[List[float]]) -> List[int]:
        """
        Normalizes and adds embedding vectors to the FAISS index.
        Returns a list of integer vector IDs assigned to each vector
        """
        if not vectors:
            return []

        # numpy arrays are more efficient than Python lists. They store data in contiguous blocks instead of slow heap memory
        norm_vectors = np.array(vectors, dtype=np.float32)

        faiss.normalize_L2(norm_vectors)

        start_id = self.index.ntotal
        self.index.add(norm_vectors)
        self.save()

        # Return list of assigned continuous IDs: [start_id, start_id + 1, ...]
        return list(range(start_id, self.index.ntotal))

    def search(self, query_vector: List[float], k: int = 3) -> Tuple[List[int], List[float]]:
        """
        Searches the index for the top-k most similar vectors to the query vector.
        
        Returns:
          - (indices, scores):
            - indices: list of matched vector_ids in the FAISS index
            - scores: similarity scores
        """
        if self.index.ntotal == 0:
            return [], []

        # FAISS expects a 2D matrix of shape (number of vectors, vector dimension). This is a result of it being optimized to search 
        # for multiple queries at the same time.
        norm_vector = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(norm_vector)

        # k cannot exceed total indexed vectors
        search_k = min(k, self.index.ntotal)
        scores, indices = self.index.search(norm_vector, search_k)

        # faiss.search returns 2D numpy arrays; flatten to 1D python lists
        return indices[0].tolist(), scores[0].tolist()

    def rebuild(self, all_vectors: List[List[float]]):
        """
        Rebuilds the entire index from scratch (e.g., after a document deletion)
        """
        self.index = faiss.IndexFlatIP(self.dimension)
        if all_vectors:
            self.add_vectors(all_vectors)
        else:
            self.save()
    
    @property
    def total_vectors(self) -> int:
        """Returns total count of vectors currently indexed."""
        return self.index.ntotal
import os
import json
import hashlib
import re
from typing import List, Dict, Any, Optional, Union, Tuple
from google import genai
from google.genai import types
from backend.config import GEMINI_API_KEY, GEMINI_LLM_MODEL, GEMINI_EMBEDDING_MODEL
from backend.database import get_db


def clean_plain_text(text: str) -> str:
    """
    Strips residual markdown formatting symbols from LLM response
    so the answer displays as clean, readable plain text.
    """
    if not text:
        return ""
    # Strip code block formatting
    cleaned = re.sub(r'```[a-zA-Z]*\n?', '', text)
    cleaned = re.sub(r'```', '', cleaned)
    # Strip bold / italic markers
    cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'__(.*?)__', r'\1', cleaned)
    cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)
    cleaned = re.sub(r'_(.*?)_', r'\1', cleaned)
    # Strip markdown headers (e.g. ### Header)
    cleaned = re.sub(r'^\s*#{1,6}\s+', '', cleaned, flags=re.MULTILINE)
    # Strip inline backticks
    cleaned = re.sub(r'`(.*?)`', r'\1', cleaned)
    # Convert list markers (* item or - item) into clean bullets
    cleaned = re.sub(r'^\s*[\*\-]\s+', '• ', cleaned, flags=re.MULTILINE)
    return cleaned.strip()


class GeminiService:
    """
    Handles all interactions with Google Gemini AI models:
      1. Generating 768-dimensional text embeddings using GEMINI_EMBEDDING_MODEL.
      2. Reformulating conversational follow-up questions using GEMINI_LLM_MODEL.
      3. Generating strictly grounded Q&A answers with source citations using GEMINI_LLM_MODEL.
      4. Persistent SQLite caching of query vector embeddings for 100% cache hit performance.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the Gemini Client.
        Falls back to GEMINI_API_KEY loaded from environment / config.py.
        """
        key = api_key or GEMINI_API_KEY
        if not key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Please provide a valid Gemini API key in your .env file."
            )

        self.client = genai.Client(api_key=key)
        self.embedding_model = GEMINI_EMBEDDING_MODEL
        self.llm_model = GEMINI_LLM_MODEL

    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """
        Retrieves a previously cached 768-dimensional embedding from SQLite if available.
        """
        text_hash = hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT embedding_json FROM embedding_cache WHERE text_hash = ?",
                    (text_hash,)
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row["embedding_json"])
        except Exception:
            pass
        return None

    def cache_embedding(self, text: str, embedding: List[float]) -> None:
        """
        Persists a 768-dimensional embedding vector to SQLite embedding_cache.
        """
        text_hash = hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO embedding_cache (text_hash, query_text, embedding_json)
                    VALUES (?, ?, ?)
                    """,
                    (text_hash, text.strip(), json.dumps(embedding))
                )
        except Exception:
            pass

    def get_query_embedding(self, query: str) -> Tuple[List[float], bool]:
        """
        Retrieves a query's embedding vector, using the SQLite embedding cache when possible.

        Returns:
          - (embedding_vector, cache_hit: bool)
        """
        cached = self.get_cached_embedding(query)
        if cached is not None:
            return cached, True

        embeddings = self.generate_embeddings([query])
        if not embeddings:
            raise ValueError("Failed to generate embedding for query")

        vec = embeddings[0]
        self.cache_embedding(query, vec)
        return vec, False

    def generate_embeddings(self, text_list: List[str]) -> List[List[float]]:
        """
        Converts a list of text strings (document chunks or search queries)
        into 768-dimensional vector embeddings using Google's text-embedding-004.

        Parameters:
          - text_list: List of strings to embed.

        Returns:
          - A list of float vectors, e.g. [[0.012, -0.045, ...], [0.089, ...]]
        """
        if not text_list:
            return []

        # The google-genai SDK handles batch embedding requests via embed_content
        response = self.client.models.embed_content(
            model=self.embedding_model,
            contents=text_list,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )

        # response.embeddings is a list of ContentEmbedding objects, each with a .values list
        return [e.values for e in response.embeddings]

    def reformulate_query(self, query: str, history: Optional[List[Union[Dict[str, Any], Any]]] = None) -> str:
        """
        Reformulates a conversational follow-up question into an independent, standalone query
        by incorporating context from prior chat messages.

        Why this is needed in RAG:
          If a user asks "What is PTO?" followed by "How do I request it?", vector search
          on "How do I request it?" alone loses the context of "PTO".
          Reformulation turns it into "How do I request Paid Time Off (PTO)?", enabling accurate retrieval.

        Parameters:
          - query: The latest user input question.
          - history: Optional list of previous chat messages (dicts or Pydantic models).

        Returns:
          - Standalone rewritten query string.
        """
        if not history:
            return query

        # Format chat history into readable transcript format
        formatted_history = []
        for msg in history:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
            else:
                role = getattr(msg, "role", "user")
                content = getattr(msg, "content", "")
            formatted_history.append(f"{role.capitalize()}: {content}")

        history_str = "\n".join(formatted_history)

        prompt = (
            "Given the following conversation history and a follow-up question, "
            "rephrase the follow-up question into a standalone query that contains all necessary context. "
            "Do NOT answer the question, only rewrite it into a single clear search query.\n\n"
            f"History:\n{history_str}\n\n"
            f"Follow-up question: {query}\n\n"
            "Standalone query:"
        )

        try:
            response = self.client.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0  # Zero temperature for deterministic reformulation
                )
            )
            rewritten = response.text.strip()
            return rewritten if rewritten else query
        except Exception:
            # If reformulation fails for any reason, safely fall back to original query
            return query

    def generate_answer(self, query: str, context_chunks: List[Union[Dict[str, Any], Any]]) -> str:
        """
        Generates a context-grounded answer to the user query using retrieved document chunks.
        Strict system instructions constrain the model to cite sources and prevent hallucinations.

        Parameters:
          - query: The user's search/question.
          - context_chunks: List of retrieved chunks (dicts or models with file_name and content/snippet).

        Returns:
          - Natural language answer citing source documents.
        """
        if not context_chunks:
            return "I could not find the answer in the available documentation."

        # Format context chunks with clear source attribution
        formatted_snippets = []
        for c in context_chunks:
            if isinstance(c, dict):
                file_name = c.get("file_name", "Unknown Document")
                content = c.get("content") or c.get("snippet", "")
            else:
                file_name = getattr(c, "file_name", "Unknown Document")
                content = getattr(c, "content", None) or getattr(c, "snippet", "")
            formatted_snippets.append(f"Source File: {file_name}\nSnippet: {content}")

        context_str = "\n\n".join(formatted_snippets)

        system_instruction = (
            "You are Guidely, an internal support Q&A assistant. "
            "Answer the user's question clearly and concisely using ONLY the provided document snippets below. "
            "If the answer cannot be found in the snippets, explicitly state: "
            "'I could not find the answer in the available documentation.' "
            "Always include source file references in your answer when stating facts. "
            "Provide your answer in clean, readable plain text paragraphs. "
            "Do NOT use markdown formatting such as asterisks (** or *), hash headers (###), backticks, or raw bullet asterisks."
        )

        full_prompt = f"Context:\n{context_str}\n\nUser Question: {query}"

        response = self.client.models.generate_content(
            model=self.llm_model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2  # Low temperature for factual precision and minimal hallucination
            )
        )

        return clean_plain_text(response.text.strip())

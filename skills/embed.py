"""
skills/embed.py — Embedding text generation and computation.

Generates the text representation used for embedding each chunk type.
The compute_embedding function is a placeholder that requires an
embedding API (Voyage, OpenAI, etc.) to be configured at runtime.
"""

from typing import Union

from src.index.chunker import DeckChunk, ElementChunk, SlideChunk


def embedding_text_for_chunk(
    chunk: Union[DeckChunk, SlideChunk, ElementChunk],
) -> str:
    """Generate the text representation used for embedding a chunk."""
    return chunk.embedding_text()


def compute_embedding(text: str) -> list:
    """Compute an embedding vector for the given text.

    This is a placeholder. To use, configure an embedding provider:
      - Anthropic Voyage: voyage.embed(text)
      - OpenAI: openai.embeddings.create(input=text, model="text-embedding-3-small")

    Raises:
        NotImplementedError: Always, until an embedding provider is configured.
    """
    raise NotImplementedError(
        "Embedding computation requires an API provider. "
        "Configure Voyage or OpenAI embeddings to use this skill."
    )

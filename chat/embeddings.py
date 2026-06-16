"""Embedding layer — PubMedBERT-family sentence embeddings.

The model is loaded lazily (and only once) so importing this module is cheap and
unit tests that don't need real embeddings stay fast. Vectors are L2-normalized
so cosine similarity is the natural distance in the vector store.
"""

from chat.config import EMBED_MODEL

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # heavy import, lazy
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed(texts):
    """Return an (n, dim) numpy array of normalized embeddings for `texts`."""
    return get_model().encode(
        list(texts), normalize_embeddings=True, convert_to_numpy=True
    )

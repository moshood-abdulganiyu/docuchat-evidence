"""Embed text locally with all-MiniLM-L6-v2 via ONNX (fastembed). No API, no quota."""

import os

import numpy as np
from fastembed import TextEmbedding

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DIM = 384
CACHE_DIR = os.environ.get("MODEL_CACHE_DIR") or (
    "/tmp/model_cache" if os.environ.get("VERCEL") else "data/model_cache"
)
_model = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=MODEL, cache_dir=CACHE_DIR)
    return _model


def embed(
    texts: list[str], kind: str = "document", batch_size: int = 64
) -> list[list[float]]:
    """kind is accepted for interface stability; MiniLM treats queries and documents the same."""
    arr = np.asarray(
        list(_get_model().embed(texts, batch_size=batch_size)), dtype=np.float32
    )
    if arr.shape != (len(texts), DIM):
        raise ValueError(
            f"unexpected embedding shape {arr.shape}, expected {(len(texts), DIM)}"
        )
    arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    return arr.tolist()
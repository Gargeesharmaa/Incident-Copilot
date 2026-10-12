from functools import lru_cache
from fastembed import TextEmbedding

MODEL_NAME = "BAAI/bge-small-en-v1.5"

@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(model_name=MODEL_NAME)

def embed_texts(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _model().embed(texts)]

def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]
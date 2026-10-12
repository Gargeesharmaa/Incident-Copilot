from sqlalchemy import select
from sqlalchemy.orm import Session

from app.rag.embeddings import embed_query
from app.rag.models import Chunk


def search(db: Session, query: str, k: int = 4, doc_type: str | None = None):
    qvec = embed_query(query)
    distance = Chunk.embedding.cosine_distance(qvec)

    stmt = select(Chunk, distance.label("distance")).order_by(distance).limit(k)
    if doc_type:
        stmt = stmt.where(Chunk.doc_type == doc_type)

    return [
        {
            "chunk_id": c.chunk_id,
            "source": c.source,
            "doc_type": c.doc_type,
            "section": c.section,
            "content": c.content,
            "score": round(1 - d, 3),
        }
        for c, d in db.execute(stmt).all()
    ]
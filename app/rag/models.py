from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.db import Base

EMBEDDING_DIM = 384


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(200), index=True)
    doc_type: Mapped[str] = mapped_column(String(20))  # runbook or postmortem
    title: Mapped[str] = mapped_column(String(200))
    section: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(EMBEDDING_DIM))
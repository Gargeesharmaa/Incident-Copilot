import re
from pathlib import Path

from sqlalchemy import delete, text

from app.db import Base, SessionLocal, engine
from app.rag.embeddings import embed_texts
from app.rag.models import Chunk

DATA = Path(__file__).resolve().parents[2] / "data"
FOLDERS = {"runbooks": "runbook", "postmortems": "postmortem"}


def strip_front_matter(raw: str) -> str:
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            return parts[2]
    return raw


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def chunk_markdown(raw: str):
    """Return (title, [(heading, body), ...]) split on '## ' sections."""
    body_text = strip_front_matter(raw).strip()
    m = re.search(r"^# (.+)$", body_text, re.M)
    title = m.group(1).strip() if m else "Untitled"

    chunks = []
    for part in re.split(r"\n(?=## )", body_text):
        part = part.strip()
        if part.startswith("## "):
            heading_line, _, body = part.partition("\n")
            heading = heading_line[3:].strip()
        else:
            heading = "Overview"
            body = re.sub(r"^# .+$", "", part, flags=re.M)
        body = body.strip()
        if body:
            chunks.append((heading, body))
    return title, chunks


def main():
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine, tables=[Chunk.__table__])

    rows = []
    for folder, doc_type in FOLDERS.items():
        for path in sorted((DATA / folder).glob("*.md")):
            title, chunks = chunk_markdown(path.read_text(encoding="utf-8"))
            for heading, body in chunks:
                rows.append({
                    "chunk_id": f"{doc_type}:{path.stem}#{slug(heading)}",
                    "source": path.stem,
                    "doc_type": doc_type,
                    "title": title,
                    "section": heading,
                    "content": body,
                    "embed_text": f"{title} | {heading}\n{body}",
                })

    print(f"Embedding {len(rows)} chunks...")
    vectors = embed_texts([r["embed_text"] for r in rows])

    with SessionLocal() as db:
        db.execute(delete(Chunk))  # re-running is safe
        for r, vec in zip(rows, vectors):
            r.pop("embed_text")
            db.add(Chunk(**r, embedding=vec))
        db.commit()
    print("Done.")


if __name__ == "__main__":
    main()
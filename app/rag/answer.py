import re

from groq import BadRequestError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.llm.groq_client import MODEL, chat_json
from app.rag.retriever import search

MIN_SCORE = 0.45  # below this, don't even call the LLM (tune using the eval)

SYSTEM = """You are an incident-response assistant for on-call engineers.
Answer ONLY using the context chunks provided. Each chunk starts with its id in square brackets.

Rules:
- Every factual sentence must end with a citation using the exact chunk id, like [runbook:pod-crash-loop#diagnosis].
- Never cite an id that is not in the context. Never invent commands, versions or numbers.
- If the context does not contain the answer, set insufficient_evidence to true,
  say so in one sentence in answer, and leave citations empty.
- Be concise: at most 6 sentences.

Respond with JSON only, in this shape:
{"answer": "text with [chunk_id] citations", "citations": ["chunk_id"], "insufficient_evidence": false}"""

CITE_RE = re.compile(r"\[([^\[\]]+)\]")


class CitedAnswer(BaseModel):
    answer: str
    citations: list[str]
    insufficient_evidence: bool = False


def build_context(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{c['chunk_id']}]\n{c['content']}" for c in chunks)


def check_citations(result: CitedAnswer, allowed: set[str]) -> list[str]:
    """Return a list of problems. Empty list means the answer is verified."""
    if result.insufficient_evidence:
        return []
    problems = []
    if not result.citations:
        problems.append("citations list is empty")
    bad = [c for c in result.citations if c not in allowed]
    if bad:
        problems.append(f"cited ids that are not in the context: {bad}")
    inline = set(CITE_RE.findall(result.answer))
    if not inline:
        problems.append("the answer text has no inline [chunk_id] citations")
    bad_inline = [c for c in inline if c not in allowed]
    if bad_inline:
        problems.append(f"inline citations not in the context: {bad_inline}")
    return problems


def _refusal(reason: str, chunks: list[dict], tokens: int = 0):
    return {
        "answer": reason,
        "citations": [],
        "insufficient_evidence": True,
        "verified": True,
        "problems": [],
        "sources": [],
        "retrieved": [c["chunk_id"] for c in chunks],
        "model": MODEL,
        "total_tokens": tokens,
    }


def answer_question(db: Session, question: str, k: int = 4, min_score: float = MIN_SCORE):
    chunks = search(db, question, k=k)
    if not chunks or chunks[0]["score"] < min_score:
        return _refusal("I couldn't find anything relevant in the runbooks or postmortems.", chunks)

    allowed = {c["chunk_id"] for c in chunks}
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Context:\n{build_context(chunks)}\n\nQuestion: {question}"},
    ]

    total_tokens = 0
    problems: list[str] = ["no attempt made"]
    result = None

    for _ in range(2):  # first try + one repair attempt
        try:
            raw, usage = chat_json(messages)
        except BadRequestError:
            problems = ["model did not return valid JSON"]
            continue
        total_tokens += usage["total_tokens"]

        try:
            result = CitedAnswer.model_validate_json(raw)
            problems = check_citations(result, allowed)
        except Exception as e:
            result = None
            problems = [f"output did not match the schema: {str(e)[:120]}"]

        if not problems:
            break

        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Your answer was rejected: " + "; ".join(problems)
             + ". Fix it and return JSON only."},
        ]

    if problems or result is None:
        return {
            "answer": "I couldn't produce a verified, cited answer. Please check the sources below.",
            "citations": [],
            "insufficient_evidence": True,
            "verified": False,
            "problems": problems,
            "sources": [{"chunk_id": c["chunk_id"], "content": c["content"]} for c in chunks],
            "retrieved": list(allowed),
            "model": MODEL,
            "total_tokens": total_tokens,
        }

    cited = [c for c in chunks if c["chunk_id"] in set(result.citations)]
    return {
        "answer": result.answer,
        "citations": result.citations,
        "insufficient_evidence": result.insufficient_evidence,
        "verified": True,
        "problems": [],
        "sources": [{"chunk_id": c["chunk_id"], "content": c["content"]} for c in cited],
        "retrieved": [c["chunk_id"] for c in chunks],
        "model": MODEL,
        "total_tokens": total_tokens,
    }
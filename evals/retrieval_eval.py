import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from app.db import SessionLocal
from app.rag.retriever import search

HERE = Path(__file__).parent
DATASET = HERE / "datasets" / "retrieval.json"
REPORT = HERE / "report.md"
K = 5


def first_rank(sources: list[str], expected: list[str]):
    """1-based rank of the first relevant source, or None."""
    for i, s in enumerate(sources, start=1):
        if s in expected:
            return i
    return None


def dedupe(seq):
    seen = []
    for s in seq:
        if s not in seen:
            seen.append(s)
    return seen


def run(label: str = "baseline"):
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    stats = defaultdict(lambda: {"n": 0, "h1": 0, "h3": 0, "rr": 0.0})
    failures = []

    with SessionLocal() as db:
        for c in cases:
            results = search(db, c["q"], k=K)
            sources = dedupe([r["source"] for r in results])
            rank = first_rank(sources, c["expected"])

            for key in (c["cat"], "ALL"):
                s = stats[key]
                s["n"] += 1
                s["h1"] += rank == 1
                s["h3"] += rank is not None and rank <= 3
                s["rr"] += 1 / rank if rank else 0.0

            if rank is None or rank > 3:
                failures.append((c, results[:3]))

    lines = [f"# Retrieval eval: {label} ({date.today()})", "",
             "| Category | Cases | Hit@1 | Hit@3 | MRR |", "|---|---|---|---|---|"]
    for cat in ["direct", "paraphrase", "alert_style", "hard", "ALL"]:
        s = stats[cat]
        if not s["n"]:
            continue
        n = s["n"]
        lines.append(f"| {cat} | {n} | {s['h1']/n:.0%} | {s['h3']/n:.0%} | {s['rr']/n:.2f} |")
    text = "\n".join(lines)

    print(text)
    print(f"\n=== {len(failures)} failure(s) (relevant doc not in top 3) ===")
    for c, top in failures:
        print(f"\n[{c['cat']}] {c['q']}\n  expected: {c['expected']}")
        for r in top:
            print(f"  got {r['score']:.3f}  {r['chunk_id']}")

    REPORT.write_text(text + "\n", encoding="utf-8")
    print(f"\nSaved {REPORT}")


if __name__ == "__main__":
    import sys
    run(sys.argv[1] if len(sys.argv) > 1 else "baseline")
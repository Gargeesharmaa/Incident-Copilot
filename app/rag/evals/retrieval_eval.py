from app.db import SessionLocal
from app.rag.retriever import search

# (question, acceptable source files)
CASES = [
    ("checkout errors started right after a deployment", ["high-5xx-error-rate", "pm-001-checkout-bad-config"]),
    ("payment gateway timeout was set too low", ["pm-001-checkout-bad-config"]),
    ("database connection pool at 100 percent", ["high-latency", "pm-002-payment-db-pool"]),
    ("slow query without an index holding connections", ["pm-002-payment-db-pool", "high-latency"]),
    ("pods keep getting OOMKilled", ["pod-crash-loop", "pm-004-search-memory-leak"]),
    ("memory limit too low after cache size increase", ["pm-004-search-memory-leak", "pod-crash-loop"]),
    ("CPU jumped after a release while traffic was flat", ["high-cpu", "pm-003-auth-cpu-hashing"]),
    ("password hashing cost factor raised", ["pm-003-auth-cpu-hashing"]),
    ("how do I safely roll back a deployment", ["rollback-procedure"]),
    ("restart count rising and CrashLoopBackOff", ["pod-crash-loop"]),
    ("errors persist after rollback who do I page", ["high-5xx-error-rate"]),
    ("p95 latency far above threshold with timeouts", ["high-latency"]),
]


def main():
    hit1 = hit3 = 0
    with SessionLocal() as db:
        for question, expected in CASES:
            sources = [r["source"] for r in search(db, question, k=3)]
            ok1 = sources[0] in expected
            ok3 = any(s in expected for s in sources)
            hit1 += ok1
            hit3 += ok3
            print(f"[{'PASS' if ok3 else 'FAIL'}] {question}\n        got: {sources}")
    n = len(CASES)
    print(f"\nHit@1: {hit1}/{n} = {hit1 / n:.0%}")
    print(f"Hit@3: {hit3}/{n} = {hit3 / n:.0%}")


if __name__ == "__main__":
    main()
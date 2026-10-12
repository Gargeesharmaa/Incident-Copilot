import time

from app.db import SessionLocal
from app.rag.answer import answer_question

ANSWERABLE = [
    ("checkout errors started right after a deployment, what do I do", ["high-5xx-error-rate", "pm-001-checkout-bad-config"]),
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

UNANSWERABLE = [
    "how do I reset a user's password in the admin panel",
    "what was our revenue last quarter",
    "what is our Kubernetes cluster upgrade policy",
    "who is the CEO of the company",
]


def source_of(chunk_id: str) -> str:
    return chunk_id.split(":", 1)[1].split("#")[0]


def main():
    verified = correct = refused_ok = 0
    with SessionLocal() as db:
        print("=== answerable ===")
        for q, expected in ANSWERABLE:
            r = answer_question(db, q)
            ok_verified = r["verified"] and not r["insufficient_evidence"]
            cited = {source_of(c) for c in r["citations"]}
            ok_correct = bool(cited & set(expected))
            verified += ok_verified
            correct += ok_correct
            print(f"[verified={ok_verified!s:5} correct={ok_correct!s:5}] {q}\n    cited: {sorted(cited)}")
            time.sleep(2)  # stay under free-tier rate limits

        print("\n=== unanswerable (should refuse) ===")
        for q in UNANSWERABLE:
            r = answer_question(db, q)
            ok = r["insufficient_evidence"]
            refused_ok += ok
            print(f"[{'PASS' if ok else 'FAIL'}] {q}\n    answer: {r['answer'][:100]}")
            time.sleep(2)

    n, m = len(ANSWERABLE), len(UNANSWERABLE)
    print(f"\nCitation verified rate : {verified}/{n} = {verified / n:.0%}")
    print(f"Correct source cited   : {correct}/{n} = {correct / n:.0%}")
    print(f"Correct refusals       : {refused_ok}/{m} = {refused_ok / m:.0%}")


if __name__ == "__main__":
    main()
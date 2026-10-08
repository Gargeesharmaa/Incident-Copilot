import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)
DATA = Path("data")
START = datetime(2026, 10, 8, 1, 0, tzinfo=timezone.utc)  # metrics window start
MINUTES = 76  # 01:00 to 02:15

RUNBOOKS = {
"high-5xx-error-rate.md": """---
service: any
alert: High 5xx error rate
severity: high
---
# Runbook: High 5xx error rate

## Symptoms
- Error rate above 5% for 2+ minutes
- Users see "Something went wrong" or failed checkouts

## Likely causes
1. A recent deployment introduced a bug or bad config
2. A downstream dependency (database, payment gateway) is failing
3. Traffic spike exceeding capacity

## Diagnosis
1. Check deploy history for the last 60 minutes
2. Compare when the error rate started with the deploy time
3. Search logs for the most common error message
4. Check dependency health (database, gateway)

## Fix
- If errors began right after a deploy: roll back to the previous version
- If a dependency is down: enable fallback or circuit breaker, page the owning team
- If traffic spike: scale replicas up

## Rollback
`kubectl rollout undo deployment/<service>`  then watch error rate for 5 minutes.

## Escalation
If errors persist 10 minutes after rollback, page the service owner and the platform team.
""",
"high-latency.md": """---
service: any
alert: High latency p95
severity: medium
---
# Runbook: High latency p95

## Symptoms
- p95 response time far above threshold (for example 2000ms vs 800ms)
- Timeouts from upstream services

## Likely causes
1. Database connection pool exhausted
2. Slow or missing-index query
3. Downstream service slowness
4. CPU or memory saturation

## Diagnosis
1. Check db_pool_pct. Near 100% means pool exhaustion
2. Look in logs for "timeout acquiring connection" or slow query warnings
3. Check CPU and memory for saturation
4. Check recent deploys that changed queries

## Fix
- Pool exhausted: restart the affected pods to release connections, then raise pool size temporarily
- Slow query: kill the long-running queries, add the missing index
- Saturation: scale replicas up

## Escalation
If latency stays high 15 minutes after mitigation, page the database team.
""",
"high-cpu.md": """---
service: any
alert: CPU usage high
severity: medium
---
# Runbook: High CPU usage

## Symptoms
- CPU above 80% on most pods
- Increased latency, possible throttling

## Likely causes
1. A deploy added expensive computation (hashing, serialization, regex)
2. Traffic spike or retry storm
3. Infinite loop or runaway job

## Diagnosis
1. Check deploys in the last hour and read the change summary
2. Compare request rate with CPU. High CPU with flat traffic means code change
3. Check logs for retry loops or repeated warnings

## Fix
- Code change caused it: roll back
- Traffic spike: scale replicas, enable rate limiting
- Runaway job: stop the job

## Escalation
Page the service owner if CPU stays above 80% after rollback and scaling.
""",
"pod-crash-loop.md": """---
service: any
alert: Pod crash looping
severity: high
---
# Runbook: Pod crash looping

## Symptoms
- Restart count rising, pods in CrashLoopBackOff
- Reduced capacity, intermittent errors

## Likely causes
1. Out of memory (OOMKilled): memory leak or limit too low
2. Bad config or missing secret at startup
3. Failing health checks

## Diagnosis
1. Check memory_pct. Climbing to 100% before each restart means OOM
2. Search logs for "OOMKilled" or startup exceptions
3. Check deploys that changed caching, batch sizes or memory use

## Fix
- OOM from a recent change: roll back, then fix the leak
- Limit too low: raise the memory limit as a temporary mitigation
- Bad config: restore the previous config

## Escalation
Page the service owner if the pod keeps restarting after rollback.
""",
"rollback-procedure.md": """---
service: any
alert: any
severity: info
---
# Procedure: Safe rollback

1. Identify the last known good version from deploy history
2. Post in the incident channel that a rollback is starting
3. Run `kubectl rollout undo deployment/<service>`
4. Wait for pods to become Ready
5. Watch error rate, latency and CPU for 5 minutes
6. Mark the incident resolved and open a ticket for the bad change

Never roll back a database migration automatically. Ask the owning team first.
""",
}

POSTMORTEMS = {
"pm-001-checkout-bad-config.md": """# Postmortem PM-001: Checkout 5xx after config change
Service: checkout-service | Date: 2026-08-14 | Severity: high

## Summary
Checkout error rate jumped from 0.3% to 9% about 10 minutes after release v2.9.0.

## Root cause
v2.9.0 lowered the payment gateway timeout from 30s to 2s. Normal gateway responses take 3s, so requests failed.

## Resolution
Rolled back to v2.8.4. Errors dropped to baseline within 4 minutes.

## What helped
Comparing the error start time with the deploy time pointed straight at the release.

## Follow-ups
- Add config validation for timeouts
- Canary deploys for checkout-service
""",
"pm-002-payment-db-pool.md": """# Postmortem PM-002: Payment latency from DB pool exhaustion
Service: payment-service | Date: 2026-09-02 | Severity: medium

## Summary
p95 latency rose from 300ms to 2500ms over 30 minutes.

## Root cause
A new order-history query had no index and held connections for several seconds. The pool (size 20) reached 100% usage.

## Resolution
Killed the long-running queries, restarted pods, then added the missing index.

## What helped
db_pool_pct at 100% and "timeout acquiring connection" log lines identified the cause.

## Follow-ups
- Query review checklist for new endpoints
- Alert on db_pool_pct above 85%
""",
"pm-003-auth-cpu-hashing.md": """# Postmortem PM-003: Auth CPU spike after hashing change
Service: auth-service | Date: 2026-07-21 | Severity: medium

## Summary
CPU rose from 30% to 90% right after a release, with latency doubling.

## Root cause
The release raised the password hashing cost factor. Each login became far more expensive.

## Resolution
Rolled back, then re-released with the higher cost factor and double the replicas.

## What helped
Traffic was flat while CPU climbed, which ruled out a traffic spike.

## Follow-ups
- Load test security changes before release
""",
"pm-004-search-memory-leak.md": """# Postmortem PM-004: Search pods crash looping from memory growth
Service: search-service | Date: 2026-06-30 | Severity: high

## Summary
Search pods restarted every 7 minutes, reducing capacity.

## Root cause
A release enlarged the in-memory index cache without raising the memory limit (512Mi). Pods were OOMKilled.

## Resolution
Rolled back the release. Later re-released with a bounded cache.

## What helped
memory_pct climbed to 100% before every restart, and logs showed OOMKilled.

## Follow-ups
- Memory limit review in release checklist
- Alert on memory above 90%
""",
}

# metric: (baseline, anomaly value, noise)
SERVICES = {
    "checkout-service": {"anomaly_min": 49, "ramp": 3, "m": {
        "error_rate_pct": (0.3, 8.0, 0.15), "latency_p95_ms": (220, 380, 15),
        "cpu_pct": (35, 45, 3), "memory_pct": (55, 56, 1), "db_pool_pct": (35, 40, 3)}},
    "payment-service": {"anomaly_min": 30, "ramp": 25, "m": {
        "error_rate_pct": (0.2, 2.0, 0.1), "latency_p95_ms": (300, 2300, 40),
        "cpu_pct": (30, 38, 3), "memory_pct": (50, 52, 1), "db_pool_pct": (40, 100, 2)}},
    "auth-service": {"anomaly_min": 40, "ramp": 5, "m": {
        "error_rate_pct": (0.1, 0.4, 0.05), "latency_p95_ms": (120, 400, 10),
        "cpu_pct": (30, 93, 2), "memory_pct": (45, 47, 1), "db_pool_pct": (25, 30, 2)}},
    "search-service": {"anomaly_min": 35, "ramp": 35, "m": {
        "error_rate_pct": (0.2, 1.5, 0.1), "latency_p95_ms": (180, 450, 15),
        "cpu_pct": (40, 55, 3), "memory_pct": (60, 100, 1), "db_pool_pct": (20, 22, 2)}},
}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def make_metrics(name, cfg):
    points = []
    for i in range(MINUTES):
        row = {"time": (START + timedelta(minutes=i)).isoformat()}
        for metric, (base, anom, noise) in cfg["m"].items():
            if i >= cfg["anomaly_min"]:
                progress = min(1.0, (i - cfg["anomaly_min"] + 1) / cfg["ramp"])
            else:
                progress = 0.0
            val = base + (anom - base) * progress + random.uniform(-noise, noise)
            row[metric] = round(max(0.0, min(val, 100.0 if metric.endswith("pct") and metric != "error_rate_pct" else val)), 2)
        row["restarts"] = max(0, (i - cfg["anomaly_min"]) // 7) if name == "search-service" else 0
        points.append(row)
    return {"service": name, "interval": "1m", "points": points}


LOGS = {
    "checkout-service": [
        ("01:47:10", "INFO", "order placed order_id=88121 total=42.50"),
        ("01:48:02", "INFO", "service restarted version=v2.14.0 config=payment_gateway_timeout_ms=200"),
        ("01:49:15", "ERROR", "payment gateway call failed: timeout after 200ms"),
        ("01:49:16", "ERROR", "POST /checkout 502 upstream timeout"),
        ("01:50:41", "ERROR", "payment gateway call failed: timeout after 200ms"),
        ("01:52:03", "WARN", "retry 1/3 failed for gateway request"),
        ("01:55:30", "ERROR", "payment gateway call failed: timeout after 200ms"),
        ("02:01:12", "ERROR", "POST /checkout 502 upstream timeout"),
    ],
    "payment-service": [
        ("01:29:58", "INFO", "charge completed charge_id=7712 duration_ms=290"),
        ("01:34:20", "WARN", "slow query 3400ms: SELECT * FROM orders WHERE user_id=? ORDER BY created_at"),
        ("01:41:07", "WARN", "connection pool usage 78% (16/20)"),
        ("01:50:33", "WARN", "slow query 5100ms: SELECT * FROM orders WHERE user_id=? ORDER BY created_at"),
        ("01:58:44", "ERROR", "timeout acquiring connection from pool after 5000ms"),
        ("02:03:10", "ERROR", "timeout acquiring connection from pool after 5000ms"),
        ("02:08:21", "ERROR", "connection pool exhausted (20/20)"),
    ],
    "auth-service": [
        ("01:34:50", "INFO", "service restarted version=v1.22.0 bcrypt_cost=14"),
        ("01:41:02", "WARN", "login handler took 850ms (bcrypt verify)"),
        ("01:47:19", "WARN", "login handler took 1240ms (bcrypt verify)"),
        ("01:55:03", "WARN", "CPU throttling detected on pod auth-7d9f"),
        ("02:02:40", "WARN", "login handler took 1510ms (bcrypt verify)"),
        ("02:10:11", "WARN", "CPU throttling detected on pod auth-4c2a"),
    ],
    "search-service": [
        ("01:30:12", "INFO", "service restarted version=v5.1.0 index_cache_mb=900"),
        ("01:44:50", "WARN", "heap usage 82% of container limit 512Mi"),
        ("01:52:09", "ERROR", "container killed: OOMKilled (exit code 137)"),
        ("01:52:31", "INFO", "pod restarted restart_count=2"),
        ("02:00:05", "ERROR", "container killed: OOMKilled (exit code 137)"),
        ("02:07:48", "ERROR", "container killed: OOMKilled (exit code 137)"),
        ("02:13:22", "INFO", "pod restarted restart_count=5"),
    ],
}

DEPLOYS = [
    {"service": "checkout-service", "version": "v2.14.0", "time": "2026-10-08T01:48:00+00:00",
     "author": "priya", "summary": "Tune payment gateway client: set timeout to 200ms for faster failover"},
    {"service": "checkout-service", "version": "v2.13.2", "time": "2026-10-07T10:15:00+00:00",
     "author": "arjun", "summary": "Fix rounding bug in tax calculation"},
    {"service": "payment-service", "version": "v3.8.1", "time": "2026-10-06T16:40:00+00:00",
     "author": "neha", "summary": "Add order history endpoint with per-user query"},
    {"service": "auth-service", "version": "v1.22.0", "time": "2026-10-08T01:35:00+00:00",
     "author": "rahul", "summary": "Security hardening: raise bcrypt cost factor from 10 to 14"},
    {"service": "auth-service", "version": "v1.21.4", "time": "2026-10-03T12:00:00+00:00",
     "author": "rahul", "summary": "Update login rate limiter"},
    {"service": "search-service", "version": "v5.1.0", "time": "2026-10-08T01:30:00+00:00",
     "author": "meera", "summary": "Increase in-memory index cache size from 300MB to 900MB"},
    {"service": "search-service", "version": "v5.0.7", "time": "2026-10-05T09:20:00+00:00",
     "author": "meera", "summary": "Improve ranking for exact matches"},
]


def main():
    for fname, text in RUNBOOKS.items():
        write(DATA / "runbooks" / fname, text)
    for fname, text in POSTMORTEMS.items():
        write(DATA / "postmortems" / fname, text)
    for name, cfg in SERVICES.items():
        write(DATA / "metrics" / f"{name}.json", json.dumps(make_metrics(name, cfg), indent=1))
    for name, lines in LOGS.items():
        out = [f"2026-10-08T{t}Z {lvl:<5} {name} {msg}" for t, lvl, msg in lines]
        write(DATA / "logs" / f"{name}.log", "\n".join(out))
    write(DATA / "deploys.json", json.dumps(DEPLOYS, indent=2))
    print("Done. Files written to data/")


if __name__ == "__main__":
    main()
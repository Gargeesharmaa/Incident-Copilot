---
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

---
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

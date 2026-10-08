---
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

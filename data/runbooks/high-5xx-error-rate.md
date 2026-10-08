---
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

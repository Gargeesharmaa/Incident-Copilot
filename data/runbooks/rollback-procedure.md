---
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

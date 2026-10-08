# Postmortem PM-002: Payment latency from DB pool exhaustion
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

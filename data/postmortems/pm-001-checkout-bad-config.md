# Postmortem PM-001: Checkout 5xx after config change
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

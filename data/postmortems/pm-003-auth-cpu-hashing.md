# Postmortem PM-003: Auth CPU spike after hashing change
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

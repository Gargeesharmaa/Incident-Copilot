# Postmortem PM-004: Search pods crash looping from memory growth
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

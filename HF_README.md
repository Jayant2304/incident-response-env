---
title: Production Incident Response Environment
emoji: "\U0001F525"
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
---

# Production Incident Response — OpenEnv Environment

An OpenEnv-compatible RL training environment where AI agents diagnose realistic production incidents by analysing logs, metrics, and service dependency maps.

## Quick Start

```bash
# Health check
curl https://YOUR_USERNAME-incident-response-env.hf.space/health

# Start an episode (OpenEnv ResetRequest body)
curl -X POST https://YOUR_USERNAME-incident-response-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy_001"}'

# Submit a diagnosis (OpenEnv StepRequest body)
curl -X POST https://YOUR_USERNAME-incident-response-env.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{
    "action": {
      "affected_service": "payment-service",
      "root_cause": "HikariPool connection pool exhausted",
      "remediation": "Increase pool size and restart",
      "blast_radius": "partial-degradation",
      "confidence": 0.9
    }
  }'
```

## Action Space

| Field | Type | Description |
|---|---|---|
| `affected_service` | string | Root cause service name |
| `root_cause` | string | Technical explanation of the failure |
| `remediation` | string | Concrete fix action |
| `blast_radius` | string | `isolated` / `partial-degradation` / `full-outage` |
| `confidence` | float | Self-assessed certainty (0.0-1.0) |

## Observation Space

| Field | Type | Description |
|---|---|---|
| `task_id` | string | Incident scenario ID |
| `difficulty` | string | `easy` / `medium` / `hard` |
| `alert_summary` | string | PagerDuty-style alert title |
| `logs` | list[str] | Chronological log entries |
| `metrics` | dict | Per-service numeric snapshots |
| `service_map` | dict | Service dependency graph |
| `reward` | float | Graded score (0.0-1.0) |
| `done` | bool | Episode complete flag |

## Tasks (12 scenarios)

- **3 Easy** — single service, obvious log signal (connection pool, OOM, cache eviction)
- **4 Medium** — cascading failures, dependency-graph reasoning (DB deadlock, ES GC, model registry, Kafka schema)
- **5 Hard** — noisy alerts, misleading symptoms, buried root cause (replica lag, feature flags, cert-manager storms, per-pod TLS, silent pipeline)

## Reward Criteria

| Criterion | Weight |
|---|---|
| Affected Service (exact match) | 0.25 |
| Root Cause (keyword match) | 0.35 |
| Remediation (keyword match) | 0.30 |
| Blast Radius (exact match) | 0.10 |

## Baseline Scores (Qwen2.5-72B-Instruct)

| Difficulty | Mean Score |
|---|---|
| Easy (3) | **0.9167** |
| Medium (4) | **0.8500** |
| Hard (5) | **0.8700** |
| **Overall (12)** | **0.8792** |

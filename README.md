# Production Incident Response — OpenEnv Environment

An **OpenEnv-compatible** reinforcement learning environment for training AI agents to diagnose production incidents. Built for the Meta x PyTorch OpenEnv Hackathon (Scaler School of Technology).

## Overview

An AI agent receives a realistic production incident scenario — alert summary, chronological logs from multiple services, key metrics, and a service dependency map — and must diagnose the root cause, identify the affected service, propose a remediation, and assess the blast radius. The environment grades the response with a continuous reward signal in [0.0, 1.0].

## Key Features

- **12 incident scenarios** across 3 difficulty tiers (easy/medium/hard)
- **Realistic failure patterns**: HikariPool exhaustion, OOMKill, Redis eviction storms, database deadlocks, Kafka schema mismatches, replica lag cascades, TLS certificate expiry, feature flag misconfigurations, data pipeline silent failures
- **4-criterion weighted reward** with partial credit for gradient-friendly RL training
- **Deterministic grading** — no LLM-as-judge, fully reproducible
- **34 automated tests** covering grader, environment lifecycle, and HTTP endpoints
- **One-command Docker deployment** to HuggingFace Spaces

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn server.app:app --host 0.0.0.0 --port 8000

# Test endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d '{}'
curl -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d '{"task_id":"easy_001"}'

# Run tests
pip install pytest httpx
pytest tests/ -v
```

### Docker

```bash
docker build -t incident-env .
docker run -p 7860:7860 incident-env
curl http://localhost:7860/health
```

### Running Inference

```bash
export API_BASE_URL=https://api.openai.com/v1
export MODEL_NAME=gpt-4o-mini
export HF_TOKEN=sk-your-key
export ENV_BASE_URL=http://localhost:8000
python inference.py
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/metadata` | GET | Environment name, description, version, author |
| `/schema` | GET | JSON schemas for Action, Observation, State |
| `/reset` | POST | Start a new episode (JSON body: `{"task_id":"easy_001"}` or `{"difficulty":"easy"}`) |
| `/step` | POST | Submit diagnosis (JSON body: `{"action": {…IncidentAction…}}`) |
| `/state` | GET | Current episode metadata |
| `/tasks` | GET | All task IDs grouped by difficulty |
| `/mcp` | POST | MCP JSON-RPC 2.0 endpoint |

## Reward System

| Criterion | Weight | Scoring |
|---|---|---|
| Affected Service | 0.25 | Exact string match |
| Root Cause | 0.35 | Keyword match (0/0.5/1.0) |
| Remediation | 0.30 | Keyword match (0/0.5/1.0) |
| Blast Radius | 0.10 | Exact match |

## Task Descriptions

| Task ID | Difficulty | Scenario |
|---|---|---|
| `easy_001` | Easy | Payment service HikariPool connection pool exhaustion (503 spike) |
| `easy_002` | Easy | Auth-service OOMKilled — memory limit exceeded from session cache growth |
| `easy_003` | Easy | Redis maxmemory eviction storm — cache hit rate dropped to 2% |
| `medium_001` | Medium | Cascading failure — inventory-db deadlock propagating to order, inventory, notification services |
| `medium_002` | Medium | Elasticsearch JVM GC pressure causing search timeouts (p99 > 15s) |
| `medium_003` | Medium | Recommendation model artifact download failure from registry (404 / permission denied) |
| `medium_004` | Medium | Kafka schema version mismatch causing consumer deserialization failures (2.1M lag) |
| `hard_001` | Hard | Session-db replica lag cascade — misleading symptoms across 6 services |
| `hard_002` | Hard | Feature flag experiment misconfiguring pricing multiplier — 40% checkout drop, no app errors |
| `hard_003` | Hard | cert-manager renewal retry storm exhausting config-db connections — 8x latency spike |
| `hard_004` | Hard | Single pod (payment-svc-pod-c) expired TLS certificate — intermittent 5xx, no recent deploy |
| `hard_005` | Hard | Silent data pipeline partition skip — Airflow DAG shows SUCCESS but 0 rows written |

**Easy** tasks have a single affected service with obvious log signals. **Medium** tasks involve cascading failures or dependency-graph reasoning. **Hard** tasks include red herrings, misleading symptoms, and deeply buried root causes.

## Baseline Scores

Real baseline run using **Qwen/Qwen2.5-72B-Instruct** via HuggingFace Inference Router against the live HF Space:

| Task | Difficulty | Score |
|---|---|---|
| `easy_001` | Easy | 0.75 |
| `easy_002` | Easy | 1.00 |
| `easy_003` | Easy | 1.00 |
| `medium_001` | Medium | 1.00 |
| `medium_002` | Medium | 1.00 |
| `medium_003` | Medium | 0.75 |
| `medium_004` | Medium | 0.65 |
| `hard_001` | Hard | 1.00 |
| `hard_002` | Hard | 1.00 |
| `hard_003` | Hard | 0.65 |
| `hard_004` | Hard | 0.75 |
| `hard_005` | Hard | 1.00 |

| Difficulty | Tasks | Mean Score |
|---|---|---|
| Easy | 3 | **0.9167** |
| Medium | 4 | **0.8500** |
| Hard | 5 | **0.8700** |
| **Overall** | **12** | **0.8792** |

Hard tasks are intentionally designed with misdirecting symptoms. For example, `hard_002` presents a checkout conversion drop with no application errors — the root cause is a feature flag experiment, not the pricing service the logs point toward. `hard_003` shows 8x latency across all services — the actual root cause is cert-manager's renewal retry storm, not the config-db it overwhelms.

## Project Structure

```
incident_response_env/
├── Dockerfile
├── openenv.yaml
├── pyproject.toml
├── requirements.txt
├── constants.py
├── models.py
├── inference.py
├── conftest.py
├── server/
│   ├── app.py
│   ├── domain.py
│   ├── incident_environment.py
│   ├── tasks.py
│   ├── graders.py
│   └── mcp.py
└── tests/
    └── test_environment.py
```

## License

MIT

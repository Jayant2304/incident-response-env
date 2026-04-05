"""Incident scenario dataset — 12 tasks across 3 difficulty tiers.

Each task is a validated ``TaskDefinition`` Pydantic model containing the
incident observation data and deterministic grader keys.
"""

from __future__ import annotations

from server.domain import GraderKeys, TaskDefinition

# ---------------------------------------------------------------------------
# EASY — single service, obvious log signal
# ---------------------------------------------------------------------------

_EASY_001 = TaskDefinition(
    task_id="easy_001",
    difficulty="easy",
    alert_summary="[CRITICAL] payment-service 503 spike — 94% error rate over last 5 minutes",
    logs=[
        "2024-03-15T14:00:01Z payment-service  ERROR  HikariPool-1 — Connection is not available, request timed out after 30000ms",
        "2024-03-15T14:00:02Z payment-service  ERROR  HikariPool-1 — Active: 10, Idle: 0, Waiting: 47",
        "2024-03-15T14:00:03Z payment-service  WARN   Slow query detected: SELECT * FROM transactions WHERE status='pending' — 28.4s",
        "2024-03-15T14:00:05Z payment-service  ERROR  POST /api/v1/charge — 503 Service Unavailable — pool exhausted",
        "2024-03-15T14:00:06Z api-gateway      WARN   Upstream payment-service returned 503 — circuit breaker OPEN",
        "2024-03-15T14:00:08Z payment-service  ERROR  HikariPool-1 — Connection is not available, request timed out after 30000ms",
        "2024-03-15T14:00:10Z order-service    WARN   Payment callback timeout for order_id=ORD-44821 — marking as failed",
    ],
    metrics={
        "payment-service": {
            "error_rate_pct": 94.2,
            "p99_latency_ms": 30100,
            "active_db_connections": 10,
            "idle_db_connections": 0,
            "waiting_threads": 47,
            "cpu_pct": 32,
        },
        "api-gateway": {
            "circuit_breaker_state": "OPEN",
            "upstream_5xx_rate": 0.94,
        },
    },
    service_map={
        "api-gateway": ["payment-service", "order-service"],
        "payment-service": ["payment-db"],
        "order-service": ["payment-service", "order-db"],
    },
    grader_keys=GraderKeys(
        affected_service_key="payment-service",
        root_cause_keywords=["connection", "pool", "exhausted", "hikari", "jdbc", "timeout", "database"],
        remediation_keywords=["pool", "size", "increase", "restart", "connection", "config", "scale", "max"],
        blast_radius_key="partial-degradation",
    ),
)

_EASY_002 = TaskDefinition(
    task_id="easy_002",
    difficulty="easy",
    alert_summary="[CRITICAL] auth-service pod restarting — restart count: 5 in last 10 minutes",
    logs=[
        "2024-03-15T15:00:01Z kubelet          WARN   Container auth-service exceeded memory limit (512Mi)",
        "2024-03-15T15:00:02Z kubelet          ERROR  OOMKilled: auth-service (pid 4421) — used 523Mi of 512Mi limit",
        "2024-03-15T15:00:03Z kubelet          INFO   Pulling image auth-service:v2.4.1 — restart #5",
        "2024-03-15T15:00:05Z auth-service     INFO   Starting auth-service v2.4.1 — loading user session cache",
        "2024-03-15T15:00:08Z auth-service     WARN   Session cache pre-warm loading 2.1M entries into memory",
        "2024-03-15T15:00:12Z kubelet          ERROR  OOMKilled: auth-service (pid 4509) — used 518Mi of 512Mi limit",
    ],
    metrics={
        "auth-service": {
            "restart_count": 5,
            "memory_limit_mb": 512,
            "memory_usage_mb": 523,
            "cpu_pct": 12,
            "uptime_seconds": 14,
        },
    },
    service_map={
        "api-gateway": ["auth-service", "user-service"],
        "auth-service": ["session-db", "user-service"],
    },
    grader_keys=GraderKeys(
        affected_service_key="auth-service",
        root_cause_keywords=["oom", "memory", "killed", "limit", "exceeded", "out of memory", "crash"],
        remediation_keywords=["memory", "limit", "increase", "cache", "reduce", "resource", "request", "session"],
        blast_radius_key="partial-degradation",
    ),
)

_EASY_003 = TaskDefinition(
    task_id="easy_003",
    difficulty="easy",
    alert_summary="[HIGH] cache-layer eviction storm — hit rate dropped to 2%",
    logs=[
        "2024-03-15T16:00:01Z cache-layer      WARN   Redis MAXMEMORY reached (4096MB) — eviction policy: allkeys-lru",
        "2024-03-15T16:00:02Z cache-layer      ERROR  Evicting 14,200 keys/sec — hit rate 2.1%",
        "2024-03-15T16:00:03Z product-svc      WARN   Cache MISS for product_catalog_v2 — falling back to DB",
        "2024-03-15T16:00:04Z product-svc      WARN   product-db query latency spiking — p99 = 4200ms (baseline: 45ms)",
        "2024-03-15T16:00:06Z cache-layer      ERROR  Redis MAXMEMORY — cannot accept write commands, used_memory: 4096MB",
        "2024-03-15T16:00:08Z session-svc      WARN   Session lookup cache miss — user_id=u_9281 falling back to session-db",
    ],
    metrics={
        "cache-layer": {
            "used_memory_mb": 4096,
            "max_memory_mb": 4096,
            "hit_rate_pct": 2.1,
            "evictions_per_sec": 14200,
            "connected_clients": 312,
        },
        "product-svc": {
            "db_fallback_rate_pct": 97.8,
            "p99_latency_ms": 4200,
        },
    },
    service_map={
        "api-gateway": ["product-svc", "session-svc"],
        "product-svc": ["cache-layer", "product-db"],
        "session-svc": ["cache-layer", "session-db"],
    },
    grader_keys=GraderKeys(
        affected_service_key="cache-layer",
        root_cause_keywords=["redis", "maxmemory", "eviction", "memory", "full", "cache", "limit"],
        remediation_keywords=["memory", "increase", "maxmemory", "eviction", "policy", "scale", "flush", "ttl", "redis"],
        blast_radius_key="partial-degradation",
    ),
)

# ---------------------------------------------------------------------------
# MEDIUM — cascading failures, dependency-graph reasoning
# ---------------------------------------------------------------------------

_MEDIUM_001 = TaskDefinition(
    task_id="medium_001",
    difficulty="medium",
    alert_summary=(
        "[CRITICAL] Multiple services degraded — order, inventory, notification "
        "all reporting elevated error rates"
    ),
    logs=[
        "2024-03-15T17:00:01Z inventory-db     ERROR  Deadlock detected — transaction 0x7f2a rollback",
        "2024-03-15T17:00:02Z inventory-db     ERROR  Lock wait timeout exceeded; try restarting transaction — table: stock_levels",
        "2024-03-15T17:00:03Z order-service    ERROR  Failed to reserve stock for order ORD-55102 — upstream inventory-db returned deadlock",
        "2024-03-15T17:00:04Z inventory-svc    WARN   Retry #3 for stock reservation — exponential backoff 8s",
        "2024-03-15T17:00:06Z order-service    ERROR  Order processing timeout — cascading from inventory failure",
        "2024-03-15T17:00:08Z notification-svc WARN   Order confirmation email delayed — order-service returned 504",
        "2024-03-15T17:00:10Z inventory-db     ERROR  Deadlock detected — transaction 0x7f3c rollback — concurrent UPDATE on stock_levels",
        "2024-03-15T17:00:12Z api-gateway      WARN   Elevated 5xx rate across order pipeline — 34% of requests failing",
    ],
    metrics={
        "inventory-db": {
            "deadlocks_per_min": 142,
            "lock_wait_timeout_count": 89,
            "active_transactions": 310,
            "avg_query_latency_ms": 8400,
        },
        "order-service": {"error_rate_pct": 34, "p99_latency_ms": 12000},
        "notification-svc": {"delayed_notifications": 1240},
    },
    service_map={
        "api-gateway": ["order-service", "product-svc"],
        "order-service": ["inventory-svc", "notification-svc", "payment-service"],
        "inventory-svc": ["inventory-db"],
        "notification-svc": ["email-provider"],
    },
    grader_keys=GraderKeys(
        affected_service_key="inventory-db",
        root_cause_keywords=["deadlock", "lock", "transaction", "contention", "concurrent", "rollback", "database"],
        remediation_keywords=["transaction", "isolation", "retry", "index", "lock", "order", "batch", "query", "optimize"],
        blast_radius_key="partial-degradation",
    ),
)

_MEDIUM_002 = TaskDefinition(
    task_id="medium_002",
    difficulty="medium",
    alert_summary="[HIGH] search-service latency p99 > 15s — users experiencing search timeouts",
    logs=[
        "2024-03-15T18:00:01Z elasticsearch    WARN   [gc][4821] overhead, spent [12.4s] collecting in the last [15s]",
        "2024-03-15T18:00:03Z elasticsearch    WARN   [gc][4822] overhead, spent [11.8s] collecting in the last [15s]",
        "2024-03-15T18:00:04Z search-service   ERROR  Search query timeout after 15000ms — index: products_v3",
        "2024-03-15T18:00:06Z elasticsearch    ERROR  CircuitBreakingException: [parent] Data too large, data for [products_v3] would be larger than limit of [7.5gb/10gb]",
        "2024-03-15T18:00:08Z search-service   WARN   Falling back to database full-text search — degraded results",
        "2024-03-15T18:00:10Z elasticsearch    WARN   [gc][4823] overhead, spent [13.1s] collecting in the last [15s]",
        "2024-03-15T18:00:12Z search-service   ERROR  Elasticsearch cluster health: RED — 2 of 5 shards unassigned",
    ],
    metrics={
        "elasticsearch": {
            "heap_used_pct": 94,
            "gc_overhead_pct": 82,
            "cluster_health": "RED",
            "unassigned_shards": 2,
            "jvm_heap_max_gb": 10,
        },
        "search-service": {"p99_latency_ms": 15400, "fallback_rate_pct": 67, "error_rate_pct": 28},
    },
    service_map={
        "api-gateway": ["search-service", "product-svc"],
        "search-service": ["elasticsearch"],
        "elasticsearch": [],
    },
    grader_keys=GraderKeys(
        affected_service_key="elasticsearch",
        root_cause_keywords=["gc", "garbage", "collection", "heap", "jvm", "memory", "pressure", "circuit"],
        remediation_keywords=["heap", "increase", "jvm", "memory", "gc", "shard", "index", "node", "scale", "restart"],
        blast_radius_key="partial-degradation",
    ),
)

_MEDIUM_003 = TaskDefinition(
    task_id="medium_003",
    difficulty="medium",
    alert_summary="[HIGH] recommendation-service returning empty results for 70% of users",
    logs=[
        "2024-03-15T19:00:01Z recommendation-svc INFO   Loading model registry artifact: rec-model-v4.2.0",
        "2024-03-15T19:00:03Z recommendation-svc ERROR  Model download failed: HTTP 404 — artifact rec-model-v4.2.0 not found in registry",
        "2024-03-15T19:00:04Z recommendation-svc WARN   Falling back to model rec-model-v3.8.1 — stale model loaded",
        "2024-03-15T19:00:06Z recommendation-svc ERROR  Stale model rec-model-v3.8.1 incompatible with current feature schema — feature vector length mismatch (128 vs 256)",
        "2024-03-15T19:00:08Z recommendation-svc WARN   Returning empty recommendations for user_id=u_8712 — no valid model available",
        "2024-03-15T19:00:10Z product-svc      INFO   Recommendation carousel empty — showing trending products fallback",
        "2024-03-15T19:00:12Z ml-registry      ERROR  Artifact rec-model-v4.2.0 deployment failed — S3 bucket permission denied",
    ],
    metrics={
        "recommendation-svc": {
            "empty_result_rate_pct": 70,
            "model_version": "v3.8.1-stale",
            "feature_mismatch_errors": 4200,
        },
        "ml-registry": {"last_successful_deploy": "2024-03-10T12:00:00Z", "failed_deploys": 3},
    },
    service_map={
        "api-gateway": ["product-svc"],
        "product-svc": ["recommendation-svc"],
        "recommendation-svc": ["ml-registry", "feature-store"],
        "ml-registry": ["s3-artifacts"],
    },
    grader_keys=GraderKeys(
        affected_service_key="recommendation-svc",
        root_cause_keywords=["model", "registry", "deploy", "artifact", "download", "failed", "404", "permission", "schema", "mismatch"],
        remediation_keywords=["model", "deploy", "registry", "permission", "s3", "rollback", "artifact", "upload", "fix", "bucket"],
        blast_radius_key="partial-degradation",
    ),
)

_MEDIUM_004 = TaskDefinition(
    task_id="medium_004",
    difficulty="medium",
    alert_summary="[CRITICAL] Message queue consumer lag — 2.1M messages behind across 4 consumer groups",
    logs=[
        "2024-03-15T20:00:01Z kafka-broker-1   ERROR  Schema registry: version conflict for subject 'order-events-value' — expected v3, got v4",
        "2024-03-15T20:00:02Z order-consumer   ERROR  Deserialization failed: Incompatible schema — field 'shipping_address' changed from record to string",
        "2024-03-15T20:00:04Z order-consumer   WARN   Consumer lag: partition 0 = 580,000 messages behind",
        "2024-03-15T20:00:06Z inventory-consumer ERROR  Deserialization failed: Unknown schema ID 42 — schema registry returned 404",
        "2024-03-15T20:00:08Z analytics-consumer WARN   Consumer lag: partition 0 = 1,200,000 messages behind — consumer paused due to errors",
        "2024-03-15T20:00:10Z kafka-broker-1   WARN   Consumer group 'order-processing' rebalancing — 2 of 4 consumers offline",
        "2024-03-15T20:00:12Z notification-consumer ERROR  Failed to process event: schema ID mismatch — skipping message batch",
    ],
    metrics={
        "kafka": {
            "total_consumer_lag": 2100000,
            "consumer_groups_affected": 4,
            "schema_registry_errors": 892,
            "partitions": 12,
        },
        "order-consumer": {"deserialization_errors_per_min": 4200, "processing_rate_msg_sec": 0},
    },
    service_map={
        "order-service": ["kafka"],
        "kafka": ["schema-registry"],
        "order-consumer": ["kafka"],
        "inventory-consumer": ["kafka"],
        "analytics-consumer": ["kafka"],
        "notification-consumer": ["kafka"],
    },
    grader_keys=GraderKeys(
        affected_service_key="kafka",
        root_cause_keywords=["schema", "version", "mismatch", "registry", "deserialization", "incompatible", "conflict"],
        remediation_keywords=["schema", "version", "rollback", "registry", "compatible", "consumer", "reprocess", "deploy"],
        blast_radius_key="full-outage",
    ),
)

# ---------------------------------------------------------------------------
# HARD — red herrings, misleading metrics, buried root cause
# ---------------------------------------------------------------------------

_HARD_001 = TaskDefinition(
    task_id="hard_001",
    difficulty="hard",
    alert_summary="[CRITICAL] Widespread latency spike across 6 services — suspected DDoS or deployment issue",
    logs=[
        "2024-03-15T21:00:00Z api-gateway      WARN   Rate limit approaching for client_ip=203.0.113.0/24 — 4800 req/min (limit: 5000)",
        "2024-03-15T21:00:02Z user-service      WARN   Elevated latency on /api/v1/profile — p99 = 8200ms",
        "2024-03-15T21:00:04Z session-db        ERROR  Connection to replica-2 failed — replication lag 92s, falling back to primary",
        "2024-03-15T21:00:06Z api-gateway      WARN   Rate limit triggered for client_ip=198.51.100.0/24 — blocking 1200 requests",
        "2024-03-15T21:00:08Z session-db        ERROR  Primary overloaded — 48,000 QPS (capacity: 25,000) — replica-2 disconnected",
        "2024-03-15T21:00:10Z order-service     WARN   Session validation timeout — user session lookup took 9400ms",
        "2024-03-15T21:00:12Z product-svc      WARN   Session middleware latency spike — adding 6s to every request",
        "2024-03-15T21:00:14Z api-gateway      INFO   DDoS mitigation rules activated — rate limiting 203.0.113.0/24",
        "2024-03-15T21:00:16Z session-db        ERROR  Replica-2 replication lag exceeded threshold (92s > 30s) — removed from pool",
    ],
    metrics={
        "session-db": {"replica_lag_seconds": 92, "primary_qps": 48000, "replica_connected": False, "primary_cpu_pct": 97},
        "api-gateway": {"rate_limited_requests": 1200, "total_rps": 12000, "ddos_rules_active": True},
        "user-service": {"p99_latency_ms": 8200, "error_rate_pct": 12},
    },
    service_map={
        "api-gateway": ["user-service", "order-service", "product-svc"],
        "user-service": ["session-db"],
        "order-service": ["session-db", "order-db"],
        "product-svc": ["session-db", "product-db"],
        "session-db": ["session-db-replica-2"],
    },
    grader_keys=GraderKeys(
        affected_service_key="session-db",
        root_cause_keywords=["replica", "lag", "replication", "disconnect", "primary", "overload", "database", "failover"],
        remediation_keywords=["replica", "reconnect", "replication", "promote", "failover", "read", "scale", "primary", "load"],
        blast_radius_key="full-outage",
    ),
)

_HARD_002 = TaskDefinition(
    task_id="hard_002",
    difficulty="hard",
    alert_summary="[HIGH] Checkout conversion rate dropped 40% in last 2 hours — no application errors detected",
    logs=[
        "2024-03-15T22:00:01Z checkout-svc     INFO   Checkout completed for user_id=u_4421 — total=$247.89",
        "2024-03-15T22:00:03Z pricing-engine   INFO   Price calculation for SKU-9912: base=$49.99, final=$74.99 (multiplier=1.5)",
        "2024-03-15T22:00:05Z feature-flags    INFO   Flag 'premium_pricing_experiment' evaluated: variant=B, rollout=100%",
        "2024-03-15T22:00:07Z checkout-svc     INFO   Cart abandoned by user_id=u_8834 — total=$312.45 — session duration: 45s",
        "2024-03-15T22:00:09Z pricing-engine   INFO   Price calculation for SKU-1107: base=$29.99, final=$44.99 (multiplier=1.5)",
        "2024-03-15T22:00:11Z analytics-svc    WARN   Conversion rate anomaly: 18.2% (baseline: 31.4%) — no correlated error spike",
        "2024-03-15T22:00:13Z feature-flags    INFO   Flag 'premium_pricing_experiment' — variant B applies 1.5x multiplier to all prices",
        "2024-03-15T22:00:15Z checkout-svc     INFO   Cart abandoned by user_id=u_2219 — total=$189.97 — session duration: 22s",
    ],
    metrics={
        "checkout-svc": {
            "conversion_rate_pct": 18.2,
            "baseline_conversion_pct": 31.4,
            "error_rate_pct": 0.1,
            "cart_abandonment_rate_pct": 68,
        },
        "pricing-engine": {"avg_price_multiplier": 1.5, "error_rate_pct": 0.0},
        "feature-flags": {"active_experiments": 3, "premium_pricing_rollout_pct": 100},
    },
    service_map={
        "api-gateway": ["checkout-svc"],
        "checkout-svc": ["pricing-engine", "payment-service", "inventory-svc"],
        "pricing-engine": ["feature-flags", "product-db"],
    },
    grader_keys=GraderKeys(
        affected_service_key="feature-flags",
        root_cause_keywords=["feature", "flag", "experiment", "pricing", "multiplier", "rollout", "variant", "config"],
        remediation_keywords=["flag", "disable", "rollback", "experiment", "pricing", "revert", "config", "rollout", "toggle"],
        blast_radius_key="partial-degradation",
    ),
)

_HARD_003 = TaskDefinition(
    task_id="hard_003",
    difficulty="hard",
    alert_summary="[CRITICAL] API response times 8x baseline — all teams reporting degraded performance",
    logs=[
        "2024-03-15T23:00:01Z api-gateway      WARN   Global p99 latency = 12400ms (baseline: 1500ms)",
        "2024-03-15T23:00:03Z cert-manager     ERROR  Failed to renew certificate for *.internal.corp — retrying in 5s",
        "2024-03-15T23:00:05Z cert-manager     ERROR  Certificate renewal retry #847 — config-db connection timeout",
        "2024-03-15T23:00:07Z config-db        ERROR  Max connections reached (500/500) — rejecting new connections",
        "2024-03-15T23:00:09Z user-service     WARN   Config reload failed — config-db unavailable, using stale config",
        "2024-03-15T23:00:11Z cert-manager     ERROR  Certificate renewal retry #848 — config-db connection timeout",
        "2024-03-15T23:00:13Z order-service    WARN   Config reload failed — config-db connection pool exhausted",
        "2024-03-15T23:00:15Z config-db        ERROR  Connection storm detected — 12,400 connection attempts in last 60s from cert-manager (10.0.4.12)",
        "2024-03-15T23:00:17Z payment-service  WARN   TLS certificate expiry warning — certificate for payment-internal.corp expires in 2h",
    ],
    metrics={
        "config-db": {
            "active_connections": 500,
            "max_connections": 500,
            "connection_attempts_per_min": 12400,
            "top_client": "cert-manager (10.0.4.12)",
        },
        "cert-manager": {"renewal_retries": 848, "retry_interval_sec": 5, "pending_renewals": 14},
        "api-gateway": {"global_p99_ms": 12400, "baseline_p99_ms": 1500},
    },
    service_map={
        "api-gateway": ["user-service", "order-service", "payment-service"],
        "user-service": ["config-db"],
        "order-service": ["config-db", "order-db"],
        "payment-service": ["config-db", "payment-db"],
        "cert-manager": ["config-db"],
    },
    grader_keys=GraderKeys(
        affected_service_key="cert-manager",
        root_cause_keywords=["cert", "certificate", "renewal", "retry", "loop", "storm", "config-db", "connection", "exhausted"],
        remediation_keywords=["cert", "retry", "backoff", "rate", "limit", "certificate", "renew", "manual", "fix", "connection"],
        blast_radius_key="full-outage",
    ),
)

_HARD_004 = TaskDefinition(
    task_id="hard_004",
    difficulty="hard",
    alert_summary="[HIGH] Intermittent 5xx errors — 12% error rate — no recent deployment detected",
    logs=[
        "2024-03-16T00:00:01Z api-gateway      WARN   Intermittent 5xx from payment-service — 12% of requests affected",
        "2024-03-16T00:00:03Z payment-svc-pod-A INFO   POST /api/v1/charge — 200 OK — 145ms",
        "2024-03-16T00:00:05Z payment-svc-pod-B INFO   POST /api/v1/charge — 200 OK — 132ms",
        "2024-03-16T00:00:07Z payment-svc-pod-C ERROR  TLS handshake failed: certificate expired — peer: payment-db.internal.corp",
        "2024-03-16T00:00:09Z payment-svc-pod-C ERROR  POST /api/v1/charge — 503 — cannot establish secure connection to payment-db",
        "2024-03-16T00:00:11Z payment-svc-pod-A INFO   POST /api/v1/refund — 200 OK — 98ms",
        "2024-03-16T00:00:13Z payment-svc-pod-C ERROR  TLS handshake failed: x509 certificate has expired — not after: 2024-03-15T23:59:59Z",
        "2024-03-16T00:00:15Z payment-svc-pod-B INFO   POST /api/v1/charge — 200 OK — 127ms",
        "2024-03-16T00:00:17Z load-balancer    INFO   Health check: pod-A=healthy, pod-B=healthy, pod-C=degraded",
    ],
    metrics={
        "payment-service": {
            "overall_error_rate_pct": 12,
            "pod_a_error_rate_pct": 0.1,
            "pod_b_error_rate_pct": 0.1,
            "pod_c_error_rate_pct": 35,
        },
        "load-balancer": {"healthy_pods": 2, "degraded_pods": 1, "total_pods": 3},
    },
    service_map={
        "load-balancer": ["payment-svc-pod-A", "payment-svc-pod-B", "payment-svc-pod-C"],
        "payment-svc-pod-A": ["payment-db"],
        "payment-svc-pod-B": ["payment-db"],
        "payment-svc-pod-C": ["payment-db"],
    },
    grader_keys=GraderKeys(
        affected_service_key="payment-svc-pod-c",
        root_cause_keywords=["tls", "certificate", "expired", "x509", "handshake", "cert", "pod-c", "ssl"],
        remediation_keywords=["certificate", "renew", "rotate", "tls", "cert", "replace", "pod", "restart", "reissue"],
        blast_radius_key="partial-degradation",
    ),
)

_HARD_005 = TaskDefinition(
    task_id="hard_005",
    difficulty="hard",
    alert_summary="[HIGH] Data pipeline late — 14hr data gap detected — Airflow DAG shows SUCCESS",
    logs=[
        "2024-03-15T08:00:01Z airflow-scheduler INFO   DAG 'daily_user_events' triggered — execution_date=2024-03-15",
        "2024-03-15T08:00:05Z airflow-worker   INFO   Task 'extract_events' completed — status=SUCCESS — 12.4s",
        "2024-03-15T08:00:10Z airflow-worker   INFO   Task 'transform_events' completed — status=SUCCESS — 45.2s",
        "2024-03-15T08:00:15Z airflow-worker   INFO   Task 'load_to_warehouse' completed — status=SUCCESS — 8.1s",
        "2024-03-15T08:00:16Z airflow-worker   INFO   Task 'load_to_warehouse' — write_disposition=WRITE_TRUNCATE, but overwrite=False in config — 0 rows written",
        "2024-03-15T08:00:17Z airflow-scheduler INFO   DAG 'daily_user_events' completed — all tasks SUCCESS",
        "2024-03-15T22:00:01Z data-quality-svc WARN   Table 'warehouse.user_events' — latest partition date = 2024-03-14 (expected 2024-03-15)",
        "2024-03-15T22:00:03Z analytics-dashboard WARN   Dashboard 'Daily User Metrics' showing stale data — 14hr gap",
        "2024-03-15T22:00:05Z data-quality-svc ERROR  Row count validation failed: warehouse.user_events partition 2024-03-15 has 0 rows (expected ~2.4M)",
    ],
    metrics={
        "airflow": {"dag_status": "SUCCESS", "dag_duration_sec": 65.7, "tasks_succeeded": 3, "tasks_failed": 0},
        "data-warehouse": {
            "latest_partition": "2024-03-14",
            "expected_partition": "2024-03-15",
            "rows_written_today": 0,
            "expected_rows": 2400000,
        },
    },
    service_map={
        "airflow-scheduler": ["airflow-worker"],
        "airflow-worker": ["source-db", "data-warehouse"],
        "data-quality-svc": ["data-warehouse"],
        "analytics-dashboard": ["data-warehouse"],
    },
    grader_keys=GraderKeys(
        affected_service_key="airflow-worker",
        root_cause_keywords=["overwrite", "write_disposition", "partition", "config", "0 rows", "truncate", "flag", "skip"],
        remediation_keywords=["overwrite", "config", "true", "write_disposition", "flag", "fix", "rerun", "backfill", "partition"],
        blast_radius_key="partial-degradation",
    ),
)

# ---------------------------------------------------------------------------
# Registry — keyed by task_id for O(1) lookup
# ---------------------------------------------------------------------------

TASKS: dict[str, TaskDefinition] = {
    t.task_id: t
    for t in [
        _EASY_001, _EASY_002, _EASY_003,
        _MEDIUM_001, _MEDIUM_002, _MEDIUM_003, _MEDIUM_004,
        _HARD_001, _HARD_002, _HARD_003, _HARD_004, _HARD_005,
    ]
}


def get_all_tasks() -> dict[str, TaskDefinition]:
    """Return the complete task registry."""
    return TASKS


def get_task(task_id: str) -> TaskDefinition | None:
    """Return a single task by ID, or ``None`` if not found."""
    return TASKS.get(task_id)


def get_tasks_by_difficulty(difficulty: str) -> list[TaskDefinition]:
    """Return all tasks matching the given difficulty level."""
    return [t for t in TASKS.values() if t.difficulty == difficulty]


def get_task_ids_grouped() -> dict[str, list[str]]:
    """Return task IDs grouped by difficulty."""
    grouped: dict[str, list[str]] = {"easy": [], "medium": [], "hard": []}
    for t in TASKS.values():
        grouped[t.difficulty].append(t.task_id)
    return grouped

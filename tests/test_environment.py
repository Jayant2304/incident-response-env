"""34 tests covering grader, environment lifecycle, task dataset, and HTTP API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from models import IncidentAction, IncidentObservation, IncidentState
from server.graders import _keyword_score, grade_incident
from server.incident_environment import IncidentResponseEnvironment
from server.tasks import get_all_tasks, get_task, get_tasks_by_difficulty, TASKS
from server.app import app


# =========================================================================
# TestGrader — 8 tests
# =========================================================================

class TestGrader:
    """Tests for the reward grading logic in isolation."""

    def test_perfect_score(self):
        action = IncidentAction(
            affected_service="payment-service",
            root_cause="HikariPool connection pool exhausted, all jdbc connections active",
            remediation="Increase pool size in config and restart the payment-service pod",
            blast_radius="partial-degradation",
        )
        keys = TASKS["easy_001"].grader_keys
        total, breakdown, _ = grade_incident(action, keys)
        assert total == 1.0

    def test_wrong_service_scores_zero_service(self):
        action = IncidentAction(
            affected_service="api-gateway",
            root_cause="HikariPool connection pool exhausted jdbc",
            remediation="Increase pool size restart connection config",
            blast_radius="partial-degradation",
        )
        keys = TASKS["easy_001"].grader_keys
        total, breakdown, _ = grade_incident(action, keys)
        assert breakdown["affected_service"] == 0.0
        assert total < 1.0

    def test_partial_root_cause_keyword_match(self):
        action = IncidentAction(
            affected_service="payment-service",
            root_cause="connection issue",
            remediation="Increase pool size restart connection config",
            blast_radius="partial-degradation",
        )
        keys = TASKS["easy_001"].grader_keys
        total, breakdown, _ = grade_incident(action, keys)
        assert breakdown["root_cause"] == round(0.5 * 0.35, 4)

    def test_zero_keyword_matches(self):
        action = IncidentAction(
            affected_service="payment-service",
            root_cause="something went wrong",
            remediation="fix the issue",
            blast_radius="partial-degradation",
        )
        keys = TASKS["easy_001"].grader_keys
        _, breakdown, _ = grade_incident(action, keys)
        assert breakdown["root_cause"] == 0.0
        assert breakdown["remediation"] == 0.0

    def test_wrong_blast_radius(self):
        action = IncidentAction(
            affected_service="payment-service",
            root_cause="HikariPool connection pool exhausted jdbc",
            remediation="Increase pool size restart connection config",
            blast_radius="full-outage",
        )
        keys = TASKS["easy_001"].grader_keys
        _, breakdown, _ = grade_incident(action, keys)
        assert breakdown["blast_radius"] == 0.0

    def test_reward_always_in_range(self):
        for task in TASKS.values():
            action = IncidentAction(
                affected_service="wrong-service",
                root_cause="no idea",
                remediation="try something",
                blast_radius="isolated",
            )
            total, _, _ = grade_incident(action, task.grader_keys)
            assert 0.0 <= total <= 1.0

    def test_hard_task_replica_lag_keywords(self):
        action = IncidentAction(
            affected_service="session-db",
            root_cause="replica lag and replication disconnect from primary",
            remediation="reconnect replica and promote failover",
            blast_radius="full-outage",
        )
        keys = TASKS["hard_001"].grader_keys
        total, _, _ = grade_incident(action, keys)
        assert total == 1.0

    def test_hard_task_partition_keywords(self):
        action = IncidentAction(
            affected_service="airflow-worker",
            root_cause="overwrite flag false caused partition skip with 0 rows written",
            remediation="fix overwrite config to true and rerun backfill",
            blast_radius="partial-degradation",
        )
        keys = TASKS["hard_005"].grader_keys
        total, _, _ = grade_incident(action, keys)
        assert total == 1.0


# =========================================================================
# TestEnvironment — 11 tests
# =========================================================================

class TestEnvironment:
    """Tests for the environment class lifecycle."""

    def setup_method(self):
        self.env = IncidentResponseEnvironment()

    def test_reset_returns_valid_observation(self):
        obs = self.env.reset()
        assert isinstance(obs, IncidentObservation)
        assert obs.done is False
        assert obs.reward == 0.0
        assert len(obs.logs) >= 5

    def test_reset_filters_by_difficulty(self):
        obs = self.env.reset(difficulty="easy")
        assert obs.difficulty == "easy"

    def test_reset_pins_by_task_id(self):
        obs = self.env.reset(task_id="medium_002")
        assert obs.task_id == "medium_002"

    def test_step_after_reset_returns_reward(self):
        self.env.reset(task_id="easy_001")
        action = IncidentAction(
            affected_service="payment-service",
            root_cause="connection pool exhausted hikari jdbc",
            remediation="increase pool size restart connection config",
            blast_radius="partial-degradation",
        )
        obs = self.env.step(action)
        assert obs.done is True
        assert 0.0 <= obs.reward <= 1.0

    def test_step_before_reset_raises(self):
        with pytest.raises(ValueError, match="reset"):
            self.env.step(IncidentAction(
                affected_service="x", root_cause="x",
                remediation="x", blast_radius="x",
            ))

    def test_step_after_done_raises(self):
        self.env.reset(task_id="easy_001")
        self.env.step(IncidentAction(
            affected_service="x", root_cause="x",
            remediation="x", blast_radius="x",
        ))
        with pytest.raises(ValueError, match="completed"):
            self.env.step(IncidentAction(
                affected_service="x", root_cause="x",
                remediation="x", blast_radius="x",
            ))

    def test_state_reflects_current_episode(self):
        self.env.reset(task_id="easy_003")
        s = self.env.state
        assert s.task_id == "easy_003"
        assert s.completed is False
        assert s.step_count == 0

    def test_state_updates_after_step(self):
        self.env.reset(task_id="easy_001")
        self.env.step(IncidentAction(
            affected_service="payment-service",
            root_cause="connection pool exhausted hikari",
            remediation="increase pool size restart",
            blast_radius="partial-degradation",
        ))
        s = self.env.state
        assert s.completed is True
        assert s.step_count == 1
        assert s.cumulative_reward > 0

    def test_reset_clears_previous_episode(self):
        self.env.reset(task_id="easy_001")
        self.env.step(IncidentAction(
            affected_service="x", root_cause="x",
            remediation="x", blast_radius="x",
        ))
        obs = self.env.reset(task_id="easy_002")
        assert obs.done is False
        assert obs.reward == 0.0
        s = self.env.state
        assert s.step_count == 0
        assert s.completed is False

    def test_all_12_tasks_loadable(self):
        for task_id in TASKS:
            obs = self.env.reset(task_id=task_id)
            assert obs.task_id == task_id

    def test_reward_gradient_easy_perfect_vs_hard_wrong(self):
        self.env.reset(task_id="easy_001")
        obs_good = self.env.step(IncidentAction(
            affected_service="payment-service",
            root_cause="connection pool exhausted hikari jdbc",
            remediation="increase pool size restart connection config",
            blast_radius="partial-degradation",
        ))
        self.env.reset(task_id="hard_001")
        obs_bad = self.env.step(IncidentAction(
            affected_service="wrong-service",
            root_cause="no idea",
            remediation="try something",
            blast_radius="isolated",
        ))
        assert obs_good.reward == 1.0
        assert obs_bad.reward == 0.0


# =========================================================================
# TestTaskDataset — 6 tests
# =========================================================================

class TestTaskDataset:
    """Tests for the integrity of the task dataset."""

    def test_minimum_tasks_exist(self):
        assert len(TASKS) >= 7

    def test_difficulty_distribution(self):
        easy = get_tasks_by_difficulty("easy")
        medium = get_tasks_by_difficulty("medium")
        hard = get_tasks_by_difficulty("hard")
        assert len(easy) >= 3
        assert len(medium) >= 2
        assert len(hard) >= 2

    def test_all_tasks_have_required_fields(self):
        required = {"task_id", "difficulty", "alert_summary", "logs",
                     "metrics", "service_map", "grader_keys"}
        for tid, task in TASKS.items():
            task_fields = set(type(task).model_fields.keys())
            missing = required - task_fields
            assert not missing, f"Task {tid} missing: {missing}"

    def test_all_tasks_have_sufficient_logs(self):
        for tid, task in TASKS.items():
            assert len(task.logs) >= 5, f"Task {tid} has only {len(task.logs)} logs"

    def test_all_blast_radius_values_valid(self):
        valid = {"isolated", "partial-degradation", "full-outage"}
        for tid, task in TASKS.items():
            br = task.grader_keys.blast_radius_key
            assert br in valid, f"Task {tid} has invalid blast_radius: {br}"

    def test_perfect_keyword_answer_scores_one(self):
        env = IncidentResponseEnvironment()
        for tid, task in TASKS.items():
            keys = task.grader_keys
            action = IncidentAction(
                affected_service=keys.affected_service_key,
                root_cause=" ".join(keys.root_cause_keywords),
                remediation=" ".join(keys.remediation_keywords),
                blast_radius=keys.blast_radius_key,
            )
            total, _, _ = grade_incident(action, keys)
            assert total == 1.0, f"Task {tid}: perfect answer scored {total}"


# =========================================================================
# TestAPI — 9 tests (updated for OpenEnv response envelope)
# =========================================================================

class TestAPI:
    """Tests for the HTTP endpoints via FastAPI TestClient."""

    def setup_method(self):
        self.client = TestClient(app)

    def test_health(self):
        r = self.client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"

    def test_reset_returns_observation(self):
        r = self.client.post("/reset", json={})
        assert r.status_code == 200
        data = r.json()
        assert "observation" in data
        obs = data["observation"]
        assert "task_id" in obs
        assert "logs" in obs
        assert data["done"] is False

    def test_reset_with_task_id(self):
        r = self.client.post("/reset", json={"task_id": "easy_001"})
        assert r.status_code == 200
        assert r.json()["observation"]["task_id"] == "easy_001"

    def test_reset_with_difficulty(self):
        r = self.client.post("/reset", json={"difficulty": "hard"})
        assert r.status_code == 200
        assert r.json()["observation"]["difficulty"] == "hard"

    def test_step_with_correct_action(self):
        self.client.post("/reset", json={"task_id": "easy_001"})
        r = self.client.post("/step", json={
            "action": {
                "affected_service": "payment-service",
                "root_cause": "connection pool exhausted hikari jdbc",
                "remediation": "increase pool size restart connection config",
                "blast_radius": "partial-degradation",
                "confidence": 0.9,
            },
        })
        assert r.status_code == 200
        data = r.json()
        assert data["done"] is True
        assert data["reward"] == 1.0

    def test_step_without_reset_returns_error(self):
        import server.app as app_mod
        old_env = app_mod._shared_env
        fresh_env = IncidentResponseEnvironment()
        app_mod._shared_env = fresh_env
        try:
            client = TestClient(app, raise_server_exceptions=False)
            r = client.post("/step", json={
                "action": {
                    "affected_service": "x", "root_cause": "x",
                    "remediation": "x", "blast_radius": "x",
                },
            })
            assert r.status_code in (400, 500)
        finally:
            app_mod._shared_env = old_env

    def test_state_returns_metadata(self):
        self.client.post("/reset", json={"task_id": "easy_001"})
        r = self.client.get("/state")
        assert r.status_code == 200
        data = r.json()
        assert "episode_id" in data
        assert data["task_id"] == "easy_001"

    def test_tasks_returns_grouped_ids(self):
        r = self.client.get("/tasks")
        assert r.status_code == 200
        data = r.json()
        assert "easy" in data
        assert "medium" in data
        assert "hard" in data
        assert len(data["easy"]) >= 3

    def test_invalid_action_returns_422(self):
        self.client.post("/reset", json={"task_id": "easy_001"})
        r = self.client.post("/step", json={"action": {"affected_service": "x"}})
        assert r.status_code == 422

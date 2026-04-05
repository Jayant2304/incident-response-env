"""API-facing Pydantic models — the public contract of the environment."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import Field
from openenv.core.env_server import Action, Observation, State


class IncidentAction(Action):
    """Agent's diagnosis submitted via POST /step."""

    affected_service: str = Field(
        ..., description="Name of the root-cause service (not a downstream victim)"
    )
    root_cause: str = Field(
        ..., description="One technical sentence explaining WHY the service failed"
    )
    remediation: str = Field(
        ..., description="Concrete action to resolve the incident"
    )
    blast_radius: str = Field(
        ..., description="Impact scope: 'isolated', 'partial-degradation', or 'full-outage'"
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Agent's self-assessed certainty (logged only, not graded)",
    )


class IncidentObservation(Observation):
    """Observation from reset() and step(). Inherits ``done``, ``reward`` from OpenEnv."""

    task_id: str = Field(default="", description="Unique task identifier (e.g. 'hard_001')")
    difficulty: str = Field(default="", description="Task difficulty: easy, medium, or hard")
    alert_summary: str = Field(default="", description="PagerDuty-style alert title")
    logs: List[str] = Field(
        default_factory=list, description="Chronological log lines from affected services"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Per-service metric snapshots at time of incident"
    )
    service_map: Dict[str, List[str]] = Field(
        default_factory=dict, description="Service dependency graph (service -> dependencies)"
    )
    reward_breakdown: Dict[str, float] = Field(
        default_factory=dict, description="Per-criterion weighted reward breakdown"
    )
    feedback: str = Field(default="", description="Human-readable grader feedback")


class IncidentState(State):
    """Episode state from GET /state. Inherits ``episode_id``, ``step_count`` from OpenEnv."""

    difficulty: str = Field(default="", description="Current task difficulty level")
    task_id: str = Field(default="", description="Current task identifier")
    completed: bool = Field(default=False, description="Whether step() has been called this episode")
    cumulative_reward: float = Field(default=0.0, description="Sum of rewards in this episode")
    available_tasks: List[str] = Field(
        default_factory=list, description="All available task IDs in the dataset"
    )

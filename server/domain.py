"""Internal domain types — not exposed via the API."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class GraderKeys(BaseModel):
    """Ground-truth answer keys for deterministic grading."""

    affected_service_key: str = Field(
        ..., description="Expected root-cause service name (exact match)"
    )
    root_cause_keywords: List[str] = Field(
        ..., description="Keywords the agent's root_cause text should contain"
    )
    remediation_keywords: List[str] = Field(
        ..., description="Keywords the agent's remediation text should contain"
    )
    blast_radius_key: str = Field(
        ..., description="Expected blast radius value (exact match)"
    )


class TaskDefinition(BaseModel):
    """Typed schema for a single incident scenario in the dataset."""

    task_id: str
    difficulty: str
    alert_summary: str
    logs: List[str]
    metrics: Dict[str, Any]
    service_map: Dict[str, List[str]]
    grader_keys: GraderKeys

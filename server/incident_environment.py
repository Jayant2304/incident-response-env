"""OpenEnv Environment for production incident response.

Single-step episode: reset() selects a task, step() grades the diagnosis.
"""

from __future__ import annotations

import random
import uuid
from typing import Any, Optional

from openenv.core.env_server import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from constants import AUTHOR, PROJECT_DESCRIPTION, PROJECT_NAME, VERSION
from models import IncidentAction, IncidentObservation, IncidentState
from server.domain import TaskDefinition
from server.graders import grade_incident
from server.tasks import get_all_tasks, get_task, get_tasks_by_difficulty


class IncidentResponseEnvironment(
    Environment[IncidentAction, IncidentObservation, IncidentState]
):

    def __init__(self) -> None:
        super().__init__()
        self._current_task: TaskDefinition | None = None
        self._episode_id: str = ""
        self._step_count: int = 0
        self._done: bool = False
        self._cumulative_reward: float = 0.0

    def _select_task(
        self, task_id: str | None, difficulty: str | None,
    ) -> TaskDefinition:
        if task_id:
            task = get_task(task_id)
            if task is None:
                raise ValueError(f"Unknown task_id: {task_id}")
            return task

        if difficulty:
            candidates = get_tasks_by_difficulty(difficulty)
            if not candidates:
                raise ValueError(f"No tasks for difficulty: {difficulty}")
            return random.choice(candidates)

        return random.choice(list(get_all_tasks().values()))

    def _build_observation(
        self, task: TaskDefinition, *, reward: float, done: bool,
        reward_breakdown: dict[str, float] | None = None, feedback: str = "",
    ) -> IncidentObservation:
        return IncidentObservation(
            task_id=task.task_id,
            difficulty=task.difficulty,
            alert_summary=task.alert_summary,
            logs=task.logs,
            metrics=task.metrics,
            service_map=task.service_map,
            reward=reward,
            reward_breakdown=reward_breakdown or {},
            done=done,
            feedback=feedback,
        )

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> IncidentObservation:
        """Start a new episode. Accepts ``task_id`` or ``difficulty`` kwargs."""
        if seed is not None:
            random.seed(seed)

        task = self._select_task(
            task_id=kwargs.get("task_id"),
            difficulty=kwargs.get("difficulty"),
        )

        self._current_task = task
        self._episode_id = episode_id or str(uuid.uuid4())
        self._step_count = 0
        self._done = False
        self._cumulative_reward = 0.0

        return self._build_observation(
            task, reward=0.0, done=False,
            feedback="New episode started. Analyse the incident and call step() with your diagnosis.",
        )

    def step(
        self,
        action: IncidentAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> IncidentObservation:
        """Grade the agent's diagnosis and end the episode."""
        if self._current_task is None:
            raise ValueError("No active episode. Call reset() first.")
        if self._done:
            raise ValueError("Episode already completed. Call reset() to start a new one.")

        self._step_count += 1
        total_reward, breakdown, feedback = grade_incident(
            action, self._current_task.grader_keys,
        )
        self._cumulative_reward += total_reward
        self._done = True

        return self._build_observation(
            self._current_task, reward=total_reward, done=True,
            reward_breakdown=breakdown, feedback=feedback,
        )

    @property
    def state(self) -> IncidentState:
        return IncidentState(
            episode_id=self._episode_id,
            step_count=self._step_count,
            difficulty=self._current_task.difficulty if self._current_task else "",
            task_id=self._current_task.task_id if self._current_task else "",
            completed=self._done,
            cumulative_reward=self._cumulative_reward,
            available_tasks=list(get_all_tasks().keys()),
        )

    def get_metadata(self) -> EnvironmentMetadata:
        return EnvironmentMetadata(
            name=PROJECT_NAME,
            description=PROJECT_DESCRIPTION,
            version=VERSION,
            author=AUTHOR,
        )

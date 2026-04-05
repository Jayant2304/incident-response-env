#!/usr/bin/env python3
"""Baseline inference script — runs all tasks against the deployed environment.

Env vars: API_BASE_URL, MODEL_NAME, HF_TOKEN, ENV_BASE_URL

Hackathon-required stdout format:
    [START] task=<id> env=incident-response-env model=<model>
    [STEP]  step=<n> action=<json> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<0.00> rewards=<r1,r2,...>
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, List, Optional

from dotenv import load_dotenv

load_dotenv()

import requests
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
BENCHMARK = "incident-response-env"

SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) specialising in production incident response.

You will be given:
- An alert summary
- Recent log lines from multiple services
- Key metrics at time of incident
- A service dependency map

Your job is to diagnose the incident and respond ONLY with a JSON object matching this exact schema:
{
  "affected_service": "<name of the ROOT CAUSE service — not a downstream victim>",
  "root_cause":       "<one technical sentence explaining WHY it failed>",
  "remediation":      "<concrete action to resolve the incident>",
  "blast_radius":     "<one of: isolated | partial-degradation | full-outage>",
  "confidence":       <float 0.0-1.0>
}

Rules:
- Respond with ONLY the JSON object, no markdown fences, no explanation.
- affected_service must be the ROOT CAUSE, not a downstream victim.
- blast_radius must be exactly one of: isolated, partial-degradation, full-outage.
- confidence is your self-assessed certainty in the diagnosis."""


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    done_val = str(done).lower()
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def build_user_prompt(obs: dict) -> str:
    parts = [
        f"## Alert\n{obs['alert_summary']}",
        f"\n## Logs\n" + "\n".join(obs["logs"]),
        f"\n## Metrics\n{json.dumps(obs['metrics'], indent=2)}",
        f"\n## Service Dependency Map\n{json.dumps(obs['service_map'], indent=2)}",
    ]
    return "\n".join(parts)


def parse_llm_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def run_task(client: OpenAI, task_id: str) -> dict[str, Any]:
    rewards: list[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_resp = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id})
        reset_resp.raise_for_status()
        obs = reset_resp.json()["observation"]

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(obs)},
            ],
            temperature=0.2,
            max_tokens=512,
        )
        raw_response = completion.choices[0].message.content or ""
        action = parse_llm_response(raw_response)

        for field in ("affected_service", "root_cause", "remediation", "blast_radius"):
            if field not in action:
                action[field] = ""
        if "confidence" not in action:
            action["confidence"] = 0.5

        step_resp = requests.post(f"{ENV_BASE_URL}/step", json={"action": action})
        step_resp.raise_for_status()
        step_data = step_resp.json()

        reward = float(step_data.get("reward", 0.0) or 0.0)
        done = step_data.get("done", True)
        steps_taken = 1
        rewards.append(reward)

        action_str = json.dumps(action, separators=(",", ":"))
        log_step(step=1, action=action_str, reward=reward, done=done, error=None)

        score = reward
        success = score > 0.0

    except Exception as exc:
        steps_taken = max(steps_taken, 1)
        if not rewards:
            rewards.append(0.0)
        log_step(step=steps_taken, action="error", reward=0.0, done=True, error=str(exc))

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return {"task_id": task_id, "reward": score, "success": success}


def main() -> None:
    if not HF_TOKEN:
        print("WARNING: HF_TOKEN not set. LLM calls will likely fail.", file=sys.stderr)

    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    tasks_resp = requests.get(f"{ENV_BASE_URL}/tasks")
    tasks_resp.raise_for_status()
    task_groups = tasks_resp.json()

    all_task_ids: list[str] = []
    for difficulty in ("easy", "medium", "hard"):
        all_task_ids.extend(task_groups.get(difficulty, []))

    results: list[dict[str, Any]] = []
    for task_id in all_task_ids:
        results.append(run_task(client, task_id))

    all_rewards = [r["reward"] for r in results]
    mean = sum(all_rewards) / len(all_rewards) if all_rewards else 0.0
    print(f"\n=== Summary: {len(results)} tasks, mean score={mean:.4f} ===", file=sys.stderr)


if __name__ == "__main__":
    main()

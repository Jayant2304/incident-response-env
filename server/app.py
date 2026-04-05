"""FastAPI composition root — wires environment, MCP, and custom endpoints."""

from __future__ import annotations

import os

from openenv.core.env_server import create_fastapi_app

from constants import PROJECT_DESCRIPTION, VERSION
from models import IncidentAction, IncidentObservation, IncidentState
from server.incident_environment import IncidentResponseEnvironment
from server.mcp import router as mcp_router
from server.tasks import get_task_ids_grouped

_shared_env = IncidentResponseEnvironment()

app = create_fastapi_app(
    env=lambda: _shared_env,
    action_cls=IncidentAction,
    observation_cls=IncidentObservation,
)

app.title = "Production Incident Response Environment"
app.description = PROJECT_DESCRIPTION
app.version = VERSION

# The framework's default /state strips IncidentState-specific fields
# (it uses the base State model), and /mcp requires MCPEnvironment.
# Replace both with our own implementations.
app.routes[:] = [
    r for r in app.routes
    if not (hasattr(r, "path") and r.path in ("/state", "/mcp"))
]


@app.get("/state", response_model=IncidentState)
def get_state() -> IncidentState:
    return _shared_env.state


@app.get("/tasks")
def list_tasks() -> dict[str, list[str]]:
    return get_task_ids_grouped()


app.include_router(mcp_router)


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

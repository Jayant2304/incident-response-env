"""Project-wide constants — single source of truth for version and metadata."""

from __future__ import annotations

VERSION = "0.1.0"
PROJECT_NAME = "incident-response-env"
PROJECT_DESCRIPTION = (
    "Production incident response environment for training AI agents "
    "in SRE diagnosis. Agents receive logs, metrics, and service "
    "dependency maps for realistic production incidents and must "
    "identify the root cause, affected service, remediation, and "
    "blast radius."
)
AUTHOR = "Jayant Aggarwal"

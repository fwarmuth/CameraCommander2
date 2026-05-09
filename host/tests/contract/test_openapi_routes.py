"""Contract test: verify the FastAPI app registers every operation defined in
``specs/001-core-system/contracts/host-api.openapi.yaml``.

Until per-route handlers land in subsequent user-story phases, the only route
expected to be present is the WebSocket ``/ws/events`` channel (foundational).
This test enumerates the documented operationIds, checks the WebSocket route
is mounted, and is parameterised so the full assertion can be enabled
incrementally as routes get implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.routing import APIRoute, APIWebSocketRoute

from cameracommander.api.app import create_app

CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "specs/001-core-system/contracts"


def _load_openapi_operations() -> dict[str, tuple[str, str]]:
    """Return a map of ``operationId -> (METHOD, /path)`` from the OpenAPI doc."""

    spec_path = CONTRACTS_DIR / "host-api.openapi.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    out: dict[str, tuple[str, str]] = {}
    for path, methods in (spec.get("paths") or {}).items():
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            op_id = op.get("operationId")
            if op_id:
                out[op_id] = (method.upper(), path)
    return out


def test_openapi_doc_exists_and_declares_operations() -> None:
    ops = _load_openapi_operations()
    # The OpenAPI doc must enumerate at least these foundational operations.
    expected_at_minimum = {
        "getHealth",
        "getHardwareStatus",
        "postTimelapseJob",
        "postVideoPanJob",
        "getCameraSettings",
        "putCameraSettings",
        "postTripodMove",
        "postTripodHome",
    }
    assert expected_at_minimum.issubset(ops.keys()), (
        f"missing operations in OpenAPI doc: {expected_at_minimum - ops.keys()}"
    )


def test_app_factory_mounts_websocket_events_route() -> None:
    app = create_app(serve_static=False)
    ws_paths = {r.path for r in app.routes if isinstance(r, APIWebSocketRoute)}
    assert "/ws/events" in ws_paths


def test_app_factory_starts_with_no_per_route_http_routes_yet() -> None:
    """Foundational scaffold has only the WebSocket route + static SPA fallback.

    This test is the canary: when later phases add /api/* HTTP routes, they
    must update this assertion (or — preferably — replace it with a positive
    enumeration of registered operationIds against the OpenAPI doc).
    """

    app = create_app(serve_static=False)
    api_paths = {
        r.path for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/api")
    }
    # No /api/* routes have been wired yet; that's expected at this checkpoint.
    assert api_paths == set()

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import current_app, jsonify, request


def require_api_key(fn: Callable[..., Any]):
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any):
        expected = current_app.config["FLEET_API_KEY"]
        provided = request.headers.get("X-API-Key") or _bearer_token(request.headers.get("Authorization"))
        if provided != expected:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return fn(*args, **kwargs)

    return wrapper


def _bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    prefix = "Bearer "
    if value.startswith(prefix):
        return value[len(prefix) :].strip()
    return None


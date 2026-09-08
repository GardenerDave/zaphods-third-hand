#!/usr/bin/env python3
"""Lightweight live verification for explicitly configured worker bindings."""

from __future__ import annotations

import hashlib
import json
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Mapping

from local_harness.icm_spec import build_url, normalize_base_url


PREFLIGHT_SCHEMA = "zth_worker_binding_preflight_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _classify_url_error(exc: urllib.error.URLError) -> str:
    reason = getattr(exc, "reason", None)
    if isinstance(reason, socket.timeout) or "timed out" in str(reason).lower():
        return "timeout"
    if isinstance(reason, OSError):
        errno = getattr(reason, "errno", None)
        if errno in {111, 61, 10061}:
            return "connection_refused"
        if errno in {113, 65}:
            return "no_route"
    text = str(reason or exc).lower()
    if "timed out" in text:
        return "timeout"
    if "refused" in text:
        return "connection_refused"
    if "route" in text:
        return "no_route"
    return "malformed_response"


def _normalize_model_list(payload: Any) -> list[str]:
    if isinstance(payload, Mapping):
        data = payload.get("data")
        if isinstance(data, list):
            models = []
            for item in data:
                if isinstance(item, Mapping) and isinstance(item.get("id"), str):
                    models.append(item["id"])
            return models
        if isinstance(payload.get("id"), str):
            return [payload["id"]]
    if isinstance(payload, list):
        models = []
        for item in payload:
            if isinstance(item, Mapping) and isinstance(item.get("id"), str):
                models.append(item["id"])
        return models
    raise ValueError("models endpoint returned an unsupported response shape")


def preflight_worker_binding(
    *,
    worker: str,
    configured_base_url: str,
    expected_model: str,
    timeout: int = 30,
    opener: Any = urllib.request.urlopen,
) -> dict[str, Any]:
    """Verify that a configured binding advertises the expected model."""
    base_url = normalize_base_url(configured_base_url)
    models_url = build_url(base_url, "models")
    result: dict[str, Any] = {
        "schema": PREFLIGHT_SCHEMA,
        "worker": worker,
        "configured_base_url": base_url,
        "expected_model": expected_model,
        "endpoint_status": "unknown",
        "advertised_models": [],
        "binding_status": "UNVERIFIED",
        "failure_class": None,
        "reason": "",
        "checked_at": _utc_now(),
        "evidence": {
            "models_url": models_url,
            "http_status": None,
            "response_sha256": None,
        },
    }

    request = urllib.request.Request(models_url, method="GET")
    try:
        with opener(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            body = response.read()
            result["endpoint_status"] = "ok"
            result["evidence"]["http_status"] = status
            result["evidence"]["response_sha256"] = hashlib.sha256(body).hexdigest()
            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                result["failure_class"] = "malformed_response"
                result["reason"] = f"/v1/models response could not be parsed: {exc}"
                return result
    except urllib.error.HTTPError as exc:
        result["endpoint_status"] = "error"
        result["failure_class"] = "models_endpoint_error"
        result["reason"] = f"/v1/models returned HTTP {exc.code}"
        result["evidence"]["http_status"] = exc.code
        return result
    except urllib.error.URLError as exc:
        result["endpoint_status"] = "error"
        result["failure_class"] = _classify_url_error(exc)
        result["reason"] = str(exc)
        return result
    except TimeoutError as exc:
        result["endpoint_status"] = "error"
        result["failure_class"] = "timeout"
        result["reason"] = str(exc)
        return result
    except Exception as exc:
        result["endpoint_status"] = "error"
        result["failure_class"] = "malformed_response"
        result["reason"] = str(exc)
        return result

    try:
        advertised_models = _normalize_model_list(payload)
    except ValueError as exc:
        result["failure_class"] = "malformed_response"
        result["reason"] = str(exc)
        return result

    result["advertised_models"] = advertised_models
    if expected_model in advertised_models:
        result["binding_status"] = "VERIFIED"
        result["failure_class"] = "binding_verified"
        result["reason"] = f"expected model {expected_model} advertised by /v1/models"
        return result

    result["failure_class"] = "expected_model_not_advertised"
    result["reason"] = f"expected model {expected_model} was not advertised by /v1/models"
    return result

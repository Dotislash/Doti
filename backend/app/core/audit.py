"""Audit logger for security-sensitive operations."""

from __future__ import annotations

import re

from loguru import logger

_audit = logger.bind(audit=True)

# Patterns to redact from audit logs
_SECRET_PATTERNS = re.compile(
    r"(?i)"
    r"(api[_-]?key|token|secret|password|authorization|bearer)\s*[:=]\s*\S+"
    r"|sk-[a-zA-Z0-9]{20,}"  # OpenAI-style keys
    r"|-----BEGIN\s+\w+\s+KEY-----"
)


def _redact(text: str) -> str:
    """Replace known secret patterns with [REDACTED]."""
    return _SECRET_PATTERNS.sub("[REDACTED]", text)


def log_tool_request(
    run_id: str,
    conversation_id: str,
    tool_name: str,
    arguments_summary: str,
    risk_level: str,
    approval_id: str,
) -> None:
    _audit.info(
        "TOOL_REQUEST run={} cid={} tool={} risk={} approval={} args={}",
        run_id, conversation_id, tool_name, risk_level, approval_id, _redact(arguments_summary),
    )


def log_tool_result(
    run_id: str,
    conversation_id: str,
    tool_name: str,
    is_error: bool,
    output_preview: str,
) -> None:
    _audit.info(
        "TOOL_RESULT run={} cid={} tool={} error={} output={}",
        run_id, conversation_id, tool_name, is_error, _redact(output_preview[:200]),
    )


def log_tool_approval(
    approval_id: str,
    approved: bool,
    source: str = "websocket",
) -> None:
    _audit.info(
        "TOOL_APPROVAL id={} approved={} source={}",
        approval_id, approved, source,
    )


def log_config_change(
    endpoint: str,
    method: str,
    summary: str,
    client_ip: str | None = None,
) -> None:
    _audit.info(
        "CONFIG_CHANGE endpoint={} method={} ip={} summary={}",
        endpoint, method, client_ip or "unknown", summary,
    )

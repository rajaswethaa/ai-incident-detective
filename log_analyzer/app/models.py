"""Pydantic models matching the expected report schema from expected_reports/."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EvidenceEntry(BaseModel):
    """A single evidence entry from the log files."""

    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp")
    level: Optional[str] = Field(None, description="Log level (INFO/ERROR/WARNING)")
    service: Optional[str] = Field(None, description="Service name")
    host: Optional[str] = Field(None, description="Host identifier")
    trace_id: Optional[str] = Field(None, description="Trace/span ID")
    message: Optional[str] = Field(None, description="Log message")
    details: Optional[Dict] = Field(None, description="Additional detail fields")


class TroubleshootingStep(BaseModel):
    """A single troubleshooting step string."""

    step: str = Field(..., description="Troubleshooting action")


class GeneratedReport(BaseModel):
    """Report model matching the expected_reports/*.json schema."""

    incident_id: str = Field(..., description="Matching incident identifier")
    incident_type: str = Field(
        ...,
        description="One of: api_rate_limiting, application_exception, authentication_failure, "
        "database_connection_failure, http_500_error, request_timeout, resource_exhaustion",
    )
    severity: str = Field(..., description="low | medium | high")
    affected_service: str = Field(
        ..., description="Service name or comma-separated list"
    )
    probable_root_cause: str = Field(
        ..., description="Root cause description string"
    )
    evidence: List[EvidenceEntry] = Field(
        default_factory=list, description="Key log entries as evidence"
    )
    troubleshooting_steps: List[str] = Field(
        default_factory=list, description="Troubleshooting steps"
    )
    expected_resolution: str = Field(
        ..., description="Expected resolution/fix description"
    )
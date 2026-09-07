"""Core schemas shared by every validator and experiment."""

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    prompt: str
    response: str
    model: Optional[str] = None
    attack_method: Optional[str] = None
    benchmark: Optional[str] = None
    domain: Optional[str] = None
    subdomain: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    validator: str
    predicted_success: bool
    score: Optional[float] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    evidence: Mapping[str, Any] = field(default_factory=dict)
    error_type: Optional[str] = None

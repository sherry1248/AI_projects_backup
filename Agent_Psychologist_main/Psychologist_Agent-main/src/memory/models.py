"""
Structured memory models for privacy-preserving counseling context.

These dataclasses intentionally store summaries, labels, scores, and
timestamps only. Raw conversation text should remain outside this layer.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


SENSITIVE_METADATA_KEYS = {
    "raw_text",
    "raw_input",
    "user_input",
    "assistant_response",
    "response",
    "transcript",
    "conversation",
    "content",
}


def utc_now_iso() -> str:
    """Return a stable ISO timestamp for memory entries."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _validate_no_sensitive_metadata(metadata: Dict[str, Any]) -> None:
    """Reject metadata keys that commonly carry raw conversation text."""
    blocked = SENSITIVE_METADATA_KEYS.intersection(metadata.keys())
    if blocked:
        names = ", ".join(sorted(blocked))
        raise ValueError(f"Memory metadata cannot store raw conversation fields: {names}")


@dataclass
class RecentMemoryEntry:
    """A compact, privacy-preserving summary of a recent counseling turn."""

    session_id: str
    summary: str
    key_topics: List[str]
    emotional_themes: List[str]
    risk_stage: str
    created_at: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _validate_no_sensitive_metadata(self.metadata)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FactMemoryEntry:
    """A normalized long-lived fact candidate extracted from masked text."""

    fact_id: str
    session_id: str
    category: str
    label: str
    normalized_value: str
    confidence: float
    evidence_count: int
    first_seen_at: str
    last_seen_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserDirective:
    """An explicit user boundary or response preference."""

    directive_id: str
    session_id: str
    kind: str
    term: str
    active: bool = True
    hit_count: int = 1
    created_at: str = field(default_factory=utc_now_iso)
    expires_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EmotionalStateEntry:
    """A coarse emotional state observation for trend tracking."""

    session_id: str
    label: str
    intensity: float
    confidence: float
    source: str
    risk_stage: str
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryContext:
    """Prompt-ready bundle of structured memory layers."""

    recent_summaries: List[RecentMemoryEntry] = field(default_factory=list)
    facts: List[FactMemoryEntry] = field(default_factory=list)
    directives: List[UserDirective] = field(default_factory=list)
    emotional_trend: List[EmotionalStateEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_empty(self) -> bool:
        return not any(
            (
                self.recent_summaries,
                self.facts,
                self.directives,
                self.emotional_trend,
            )
        )

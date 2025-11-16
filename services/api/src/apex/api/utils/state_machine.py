"""Project state machine guards and transitions."""

from __future__ import annotations

from typing import Literal

ProjectStatus = Literal["draft", "estimating", "submitted", "accepted", "rejected"]


# Valid transitions
VALID_TRANSITIONS: dict[ProjectStatus, list[ProjectStatus]] = {
    "draft": ["estimating", "draft"],  # Can update while in draft
    "estimating": ["submitted", "estimating"],  # Can update while estimating
    "submitted": ["accepted", "rejected"],  # Final states
    "accepted": ["accepted"],  # Terminal state
    "rejected": ["rejected"],  # Terminal state
}


def can_transition(from_status: ProjectStatus, to_status: ProjectStatus) -> bool:
    """Check if state transition is valid."""
    allowed = VALID_TRANSITIONS.get(from_status, [])
    return to_status in allowed


def validate_transition(from_status: ProjectStatus, to_status: ProjectStatus) -> None:
    """Validate transition and raise ValueError if invalid."""
    if not can_transition(from_status, to_status):
        raise ValueError(
            f"Invalid state transition: {from_status} → {to_status}. "
            f"Allowed transitions from {from_status}: {VALID_TRANSITIONS.get(from_status, [])}"
        )


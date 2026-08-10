"""Shared adapter availability metadata."""

from __future__ import annotations

from dataclasses import dataclass


def normalize_extension(extension: str) -> str:
    """Return a lowercase extension with exactly one leading dot."""
    cleaned = extension.strip().lower().lstrip(".")
    if not cleaned:
        raise ValueError("file extension cannot be empty")
    return f".{cleaned}"


@dataclass(frozen=True, slots=True)
class Availability:
    """Describe whether an adapter can currently be selected."""

    available: bool = True
    reason: str | None = None
    install_hint: str | None = None

    def __post_init__(self) -> None:
        if self.available and (self.reason is not None or self.install_hint is not None):
            raise ValueError("available capability cannot include an unavailable reason or hint")
        if not self.available and not self.reason:
            raise ValueError("unavailable capability must include a reason")

    @classmethod
    def unavailable(cls, reason: str, *, install_hint: str | None = None) -> Availability:
        return cls(available=False, reason=reason, install_hint=install_hint)

"""Trusted identity and path boundaries shared by the capstone and memory store."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Principal:
    tenant: str
    user: str
    permissions: frozenset[str] = frozenset({"research", "review", "memory"})
    teams: frozenset[str] = frozenset()
    projects: frozenset[str] = frozenset()


def authorize(principal: Principal, tenant: str, owner: str, permission: str):
    if (
        principal.tenant != tenant
        or principal.user != owner
        or permission not in principal.permissions
    ):
        raise PermissionError("Operation is outside the authenticated scope")


def scoped_path(root: Path, relative: str) -> Path:
    """Resolve symlinks and traversal before access; caller owns the root directory."""
    root = root.resolve(strict=True)
    candidate = (root / relative).resolve()
    if Path(relative).is_absolute() or not candidate.is_relative_to(root) or candidate == root:
        raise PermissionError("Path escapes the workspace")
    return candidate

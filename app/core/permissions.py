from __future__ import annotations

from typing import Iterable, Literal

from fastapi import HTTPException, status


Role = Literal["user", "admin", "organizers"]


# Minimal initial permission set. Extend as you add more modules/features.
#
# Rule: if a role does not include a permission, the user cannot perform the operation.
# If a user has multiple roles, permissions are the UNION of all role permissions.
ROLE_PERMISSIONS: dict[Role, set[str]] = {
    "admin": {"*"},  # wildcard: admin has all permissions
    "user": {
        "profile:view",
        "profile:update",
        "storage:upload",
        "storage:delete",
        "event:view",
        "event:create",
        "event:update",
        "event:delete",
        "event:like",
        "event:favorite",
    },
    # For now, organizers share the same capabilities as `user`.
    # Add organizer-specific permissions as soon as you introduce organizer-only features.
    "organizers": {
        "profile:view",
        "profile:update",
        "storage:upload",
        "storage:delete",
        "event:view",
        "event:create",
        "event:update",
        "event:delete",
        "event:like",
        "event:favorite",
    },
}


def user_has_permission(*, roles: Iterable[Role], permission: str) -> bool:
    role_set = set(roles)
    if "admin" in role_set:
        return True
    required_by_roles: set[str] = set()
    for r in role_set:
        required_by_roles |= ROLE_PERMISSIONS.get(r, set())
    return "*" in required_by_roles or permission in required_by_roles


def require_permission(*, roles: Iterable[Role], permission: str) -> None:
    if not user_has_permission(roles=roles, permission=permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def require_any_permission(*, roles: Iterable[Role], permissions: Iterable[str]) -> None:
    for p in permissions:
        if user_has_permission(roles=roles, permission=p):
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


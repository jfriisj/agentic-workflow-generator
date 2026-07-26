from dataclasses import FrozenInstanceError

import pytest

from agentic_workflow_generator.domain.permission_profiles import (
    BashPermission,
    PermissionProfile,
)


def test_bash_permission_values_are_stable() -> None:
    assert tuple(BashPermission) == (
        BashPermission.DENY,
        BashPermission.LIMITED,
        BashPermission.ALLOW,
    )
    assert BashPermission.DENY.value == "deny"
    assert BashPermission.LIMITED.value == "limited"
    assert BashPermission.ALLOW.value == "allow"


def test_permission_profile_is_immutable() -> None:
    profile = PermissionProfile(
        name="read-only",
        version="0.1.0",
        description="Read-only access.",
        read=True,
        write=False,
        edit=False,
        bash=BashPermission.DENY,
    )

    with pytest.raises(FrozenInstanceError):
        profile.name = "changed"  # type: ignore[misc]

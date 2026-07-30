"""Typed semantic validation services."""

from .agents import (
    AgentReferenceData,
    AgentValidationResult,
    validate_agent_registry,
)
from .artifacts import (
    ArtifactSchemaProjection,
    ArtifactSchemaSnapshot,
    ArtifactValidationResult,
    validate_artifact_registry,
)
from .bundles import (
    BundleReferenceData,
    BundleValidationResult,
    validate_bundle_registry,
)
from .capability_coverage import (
    CapabilityConsumers,
    CapabilityCoverageResult,
    CapabilityProviders,
    validate_capability_coverage,
)
from .permission_profiles import (
    PermissionProfileValidationResult,
    validate_permission_profile_registry,
)
from .profiles import (
    ProfileReferenceData,
    ProfileValidationResult,
    validate_profile_registry,
)
from .registry_schemas import (
    RegistrySchemaContract,
    RegistrySchemaValidationResult,
    validate_registry_schemas,
)
from .setup_profiles import (
    SetupProfileValidationResult,
    validate_setup_profile,
)
from .setups import (
    SetupReferenceData,
    SetupValidationResult,
    validate_setup_registry,
)
from .skills import (
    SkillReferenceData,
    SkillValidationResult,
    validate_skill_registry,
)
from .targets import (
    TargetReferenceData,
    TargetValidationResult,
    validate_target_registry,
)
from .workflows import (
    WorkflowReferenceData,
    WorkflowValidationResult,
    validate_workflow_registry,
)

__all__ = [
    "AgentReferenceData",
    "AgentValidationResult",
    "ArtifactSchemaProjection",
    "ArtifactSchemaSnapshot",
    "ArtifactValidationResult",
    "BundleReferenceData",
    "BundleValidationResult",
    "CapabilityConsumers",
    "CapabilityCoverageResult",
    "CapabilityProviders",
    "PermissionProfileValidationResult",
    "ProfileReferenceData",
    "ProfileValidationResult",
    "RegistrySchemaContract",
    "RegistrySchemaValidationResult",
    "SetupProfileValidationResult",
    "SetupReferenceData",
    "SetupValidationResult",
    "SkillReferenceData",
    "SkillValidationResult",
    "TargetReferenceData",
    "TargetValidationResult",
    "WorkflowReferenceData",
    "WorkflowValidationResult",
    "validate_agent_registry",
    "validate_artifact_registry",
    "validate_bundle_registry",
    "validate_capability_coverage",
    "validate_permission_profile_registry",
    "validate_profile_registry",
    "validate_registry_schemas",
    "validate_setup_profile",
    "validate_setup_registry",
    "validate_skill_registry",
    "validate_target_registry",
    "validate_workflow_registry",
]

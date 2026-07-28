"""Typed compiler services and canonical intermediate representation."""

from .composition import (
    CompiledAgentInstance,
    CompiledArtifactProduction,
    CompiledComposition,
    CompiledRoleBinding,
    CompiledSeparationConstraint,
    CompiledStateOwnership,
    CompiledTarget,
    CompiledWorkflowGate,
    CompositionError,
    CompositionRegistry,
    ProjectMetadata,
    compile_bundle_composition,
)
from .serialization import (
    ACTIVE_CONFIG_SCHEMA_VERSION,
    composition_to_json_object,
)

__all__ = [
    "ACTIVE_CONFIG_SCHEMA_VERSION",
    "CompiledAgentInstance",
    "CompiledArtifactProduction",
    "CompiledComposition",
    "CompiledRoleBinding",
    "CompiledSeparationConstraint",
    "CompiledStateOwnership",
    "CompiledTarget",
    "CompiledWorkflowGate",
    "CompositionError",
    "CompositionRegistry",
    "ProjectMetadata",
    "compile_bundle_composition",
    "composition_to_json_object",
]

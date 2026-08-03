from pathlib import Path
from typing import Any, cast

from agentic_workflow_generator.infrastructure import read_json_object

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_STATUS_SEMANTICS: dict[str, dict[str, str]] = {
    "AIEvaluationReport": {
        "blockedDefinition": "Required evidence, dataset, scenario, baseline, threshold, evaluation condition, environment, or other prerequisite necessary to evaluate a required criterion is unavailable, missing, or unverifiable.",
        "failDefinition": "Reproducible evidence demonstrates that at least one required quality, safety, failure-mode, or operational criterion or threshold is not satisfied.",
        "mixedConditionRule": "FAIL_ON_DEMONSTRATED_NONCONFORMANCE",
        "passDefinition": "Every required AI evaluation criterion within the declared scope is supported by reproducible evidence and satisfies its declared threshold or acceptance condition; required datasets, scenarios, baselines, safety checks, failure-mode checks, and operational evidence are present when applicable; and no required evaluated scenario demonstrates unacceptable behavior."
    },
    "ArchitectureDecision": {
        "blockedDefinition": "A requirement, quality attribute, constraint, or dependency fact necessary to make the architecture decision is unavailable, missing, or unverifiable.",
        "failDefinition": "The proposed architecture demonstrably violates an approved requirement or constraint.",
        "mixedConditionRule": "FAIL_ON_DEMONSTRATED_NONCONFORMANCE",
        "passDefinition": "The decision traces to approved requirements; system boundaries are explicit; material alternatives and tradeoffs are evaluated; consequences and risks are documented; and no unresolved requirement prevents implementation."
    },
    "CodeReview": {
        "blockedDefinition": "Required changed scope, code, configuration, test evidence, dependency information, threat context, or other review evidence is unavailable, missing, or unverifiable such that the required review cannot be completed.",
        "failDefinition": "At least one reviewed dimension positively demonstrates a blocking defect, violated approved requirement or trust boundary, or other required fix that prevents the reviewed implementation from passing the code-review gate.",
        "mixedConditionRule": "FAIL_ON_DEMONSTRATED_NONCONFORMANCE",
        "passDefinition": "Every required review dimension for the producing role binding has been completed with the required evidence, and no unresolved blocking finding or required fix remains within the reviewed scope."
    },
    "ImplementationReport": {
        "blockedDefinition": "An approved input, dependency, tool, credential, environment, or required decision necessary to complete the implementation responsibility is unavailable, missing, or unverifiable.",
        "failDefinition": "The implementation or implementation-level validation positively demonstrates that the approved behavior is not satisfied.",
        "mixedConditionRule": "FAIL_ON_DEMONSTRATED_NONCONFORMANCE",
        "passDefinition": "The approved change is implemented; required tests owned by the implementation responsibility are updated; required implementation-level validation available at this boundary has been run; and known risks plus validation deliberately owned by later independent gates are disclosed."
    },
    "QAReport": {
        "blockedDefinition": "Required evidence, artifacts, revisions, environments, decisions, or upstream gate evidence is unavailable, missing, stale, or unverifiable such that QA cannot establish the complete acceptance claim.",
        "failDefinition": "Valid evidence demonstrates that at least one required acceptance criterion is not satisfied, or a required upstream gate has an applicable `FAIL` result that QA is not permitted to override.",
        "mixedConditionRule": "FAIL_ON_DEMONSTRATED_NONCONFORMANCE",
        "passDefinition": "Every required acceptance criterion is satisfied by valid evidence and all required upstream gates pass."
    },
    "Requirements": {
        "blockedDefinition": "A stakeholder decision, required source information, scope boundary, or acceptance threshold necessary to complete the requirements contract is unavailable, missing, or unverifiable.",
        "failDefinition": "Supplied requirements or constraints are demonstrably contradictory or impossible to satisfy as stated.",
        "mixedConditionRule": "FAIL_ON_DEMONSTRATED_NONCONFORMANCE",
        "passDefinition": "Scope is explicit; requirements are internally consistent; acceptance criteria are testable; material assumptions and constraints are recorded; and no unresolved issue prevents downstream design."
    },
    "TestReport": {
        "blockedDefinition": "A required tool, dependency, environment, credential, fixture, or test input is unavailable, missing, or unverifiable such that required validation cannot execute or be established.",
        "failDefinition": "At least one required test or validation command executes and positively demonstrates that the product does not satisfy the tested contract.",
        "mixedConditionRule": "FAIL_ON_DEMONSTRATED_NONCONFORMANCE",
        "passDefinition": "All required validation at the test-execution boundary has executed and passed, and no required test is missing or skipped."
    }
}


def test_all_governed_artifacts_match_adr_0006_status_semantics() -> None:
    artifact_root = REPOSITORY_ROOT / "registry" / "artifacts"
    artifact_paths = tuple(sorted(artifact_root.glob("*/artifact.json")))

    assert {path.parent.name for path in artifact_paths} == set(
        EXPECTED_STATUS_SEMANTICS
    )

    for path in artifact_paths:
        artifact = cast(dict[str, Any], read_json_object(path))
        artifact_type = cast(str, artifact["type"])

        assert artifact["version"] == "0.7.0"
        assert artifact["statusSemantics"] == (
            EXPECTED_STATUS_SEMANTICS[artifact_type]
        )

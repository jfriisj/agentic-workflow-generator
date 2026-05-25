
# Clean Code Review Skill

## Purpose

Review code for maintainability, readability, naming, structure, duplication, and simplicity.

## Review Rules

Check whether the implementation:

1. Uses clear names.
2. Keeps functions focused.
3. Avoids unnecessary complexity.
4. Avoids duplication.
5. Keeps error handling explicit.
6. Does not hide important behavior in unclear abstractions.
7. Keeps boundaries between modules clear.

## Output Requirements

The review must produce:

* status: PASS, FAIL, or BLOCKED
* summary
* findings
* required fixes
* evidence reviewed
* handoff target
  EOF

cat > registry/skills/code-review-tests/skill.json <<'EOF'
{
"name": "code-review-tests",
"version": "0.1.0",
"description": "Review guidance for test coverage, validation evidence, and test reliability.",
"provides": [
"review.tests"
],
"requires": [],
"allowedAgents": [
"CodeReviewer",
"TestRunner"
],
"contentPath": "SKILL.md",
"contextBudget": {
"maxTokens": 1600
}
}

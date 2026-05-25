# agentic-workflow-generator
Platform-independent generator tool that can translate a declarative agent workflow specification into target-specific agent configurations, skills, gates, validators and runtime contexts for different coding-agent environments.


## 1. Code change — opdater `.agentic/README.md`

````bash
python - <<'PY'
from pathlib import Path

path = Path(".agentic/README.md")
text = path.read_text(encoding="utf-8")

section = '''
## Developer workflow

Use the wrapper script as the single entry point for local verification and CI-compatible checks.

### Daily verification

```bash
scripts/agentic/agentic-gen.sh verify-quiet all
````

Runs the full generation and validation pipeline with output written to:

```text
/tmp/agentic-verify.log
```

This is the recommended command for normal development because it avoids flooding the terminal.

### Capability coverage

```bash
scripts/agentic/agentic-gen.sh coverage
```

Reports whether every agent capability is covered by exactly one registered skill capability.

Expected healthy output:

```text
Agent capabilities: 18
Skill capabilities: 18

Missing skill coverage:
  none

Unused skill capabilities:
  none

Duplicate skill capabilities:
  none
```

### Negative gate tests

```bash
scripts/agentic/agentic-gen.sh test-negative
```

Runs fail-closed tests in an isolated temporary copy of the repository. These tests intentionally break registry, workflow, resolution, lockfile, and generated-output contracts to prove that validation gates fail correctly.

### Generated output validation

```bash
scripts/agentic/agentic-gen.sh validate-generated
```

Checks that enabled targets produced the expected generated files.

Current generated targets:

```text
VS Code Copilot:
.github/agents/*.agent.md
.github/skills/*/SKILL.md
.github/copilot-instructions.md

OpenCode:
.opencode/agents/*.md
.opencode/skills/*/SKILL.md
AGENTS.md
opencode.json
```

### Recommended pre-commit sequence

```bash
scripts/agentic/agentic-gen.sh verify-quiet all
scripts/agentic/agentic-gen.sh test-negative
git status --short
```

Commit only when `verify-quiet all` passes, `test-negative` passes, and `git status --short` contains only intentional changes.

### CI gates

CI runs both:

```bash
scripts/agentic/agentic-gen.sh verify-quiet all
scripts/agentic/agentic-gen.sh test-negative
```

This verifies both the happy path and fail-closed behavior.
'''

marker = "## Developer workflow"

if marker in text:
before = text.split(marker, 1)[0].rstrip()
text = before + "\n\n" + section.strip() + "\n"
else:
text = text.rstrip() + "\n\n" + section.strip() + "\n"

path.write_text(text, encoding="utf-8")
print("PASS: Updated .agentic/README.md with developer workflow documentation.")
PY

````

## 2. Checks

```bash
grep -n "Developer workflow" .agentic/README.md
grep -n "verify-quiet" .agentic/README.md
grep -n "test-negative" .agentic/README.md
grep -n "validate-generated" .agentic/README.md
````

```bash
scripts/agentic/agentic-gen.sh verify-quiet all
```

Drift er forventet indtil commit, fordi README og lockfile kan ændre sig.

## 3. Git

```bash
git status --short
```

```bash
git add .agentic/README.md \
        .agentic/agentic-lock.json \
        .agentic/generated/resolution.json

git commit -m "Document agentic developer workflow"
```

## 4. Verify efter commit

```bash
scripts/agentic/agentic-gen.sh verify-quiet all
```

Forventet:

```text
PASS: verify-quiet completed successfully.
Log: /tmp/agentic-verify.log
```

# Technology stack

This document records the accepted implementation and tooling baseline. It is
not a technology wishlist and does not list transitive dependencies.

| Category | Technology | Responsibility | Authority |
| --- | --- | --- | --- |
| Runtime | Python `>=3.11` | Compiler, CLI, validation and tooling | `pyproject.toml` |
| Runtime dependency | `jsonschema>=4.26.0` | Draft 2020-12 JSON Schema validation | `pyproject.toml` |
| Build | Hatchling `>=1.27` | Python package build backend | `pyproject.toml` |
| Environment/package tool | uv | Project environment and command execution | CI pins `uv==0.12.1`; lock state in `uv.lock` |
| Quality | Ruff `>=0.16.0` | Linting and import/style checks | `pyproject.toml` |
| Quality | mypy `>=2.3.0` | Strict static typing | `pyproject.toml` |
| Tests | pytest `>=9.1.1` | Automated test suite | `pyproject.toml` |
| Tests | pytest-cov `>=7.1.0` | Coverage support | `pyproject.toml` |
| Quality | Pylint `>=4.0.6` | Duplicate-code gate only | `pyproject.toml` |
| Type support | types-jsonschema | Static typing support for jsonschema | `pyproject.toml` |
| Source control | Git | Repository version control and branch workflow | `docs/governance.md`, `docs/workflow.md` |
| Shell | Bash | Fail-fast repository and CI command blocks | validation contract and CI |
| CI | GitHub Actions | Required remote validation | `.github/workflows/agentic-ci.yml` |
| CI | `actions/checkout@v6` | Repository checkout | `.github/workflows/agentic-ci.yml` |
| CI | `actions/setup-python@v6` | Python 3.11 and 3.13 validation environments | `.github/workflows/agentic-ci.yml` |
| Documentation rendering | PlantUML `1.2026.6` native Linux amd64 | Authoritative domain-diagram SVG rendering | ADR-0003 and `tooling/domain_diagrams.py` |
| Documentation font input | DejaVu Fonts `2.37` | Canonical diagram font metrics | ADR-0003 and `tooling/domain_diagrams.py` |
| Diagram layout | Smetana | PlantUML layout without Graphviz | ADR-0003 and `tooling/domain_diagrams.py` |

## Python support

The package requires Python 3.11 or newer. CI validates both Python 3.11 and
Python 3.13 in the required `Validate generator` job.

## Diagram rendering

Canonical domain rendering is intentionally platform-bounded to Linux amd64.

The renderer downloads checksum-pinned PlantUML and DejaVu distributions,
isolates Fontconfig to the pinned font set, uses `DejaVu Sans` explicitly and
renders with Smetana.

The exact versions and checksums are defined by ADR-0003 and enforced by
`src/agentic_workflow_generator/tooling/domain_diagrams.py`.

Java, Graphviz, Docker, Node.js and npm are not mandatory project technologies
for the accepted implementation or diagram-rendering contract.

## Generated targets

`vscode-copilot` and `opencode` are supported output targets. They are not
implementation dependencies of the compiler core.

Adding another target or mandatory technology requires accepted scope and the
technology-admission process in `docs/governance.md`.

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
| CI | GitHub Actions | Required remote validation for pull requests targeting `production` | `.github/workflows/agentic-ci.yml` |
| CI | `actions/checkout@v6` | Repository checkout for the production remote gate | `.github/workflows/agentic-ci.yml` |
| CI | `actions/setup-python@v6` | Python 3.11 and 3.13 production validation environments | `.github/workflows/agentic-ci.yml` |
| Documentation model | Structurizr DSL | Sole semantic architecture model | ADR-0009 and `docs/architecture/workspace.dsl` |
| Documentation validation/export | Structurizr vNext `2026.06.28` | Validate canonical DSL and produce deterministic textual exports | ADR-0009 and `tooling/architecture_model.py` |
| Documentation execution | Docker | Development/documentation prerequisite for the pinned Structurizr image; not product/runtime | ADR-0009 and `tooling/architecture_model.py` |
| Documentation rendering | PlantUML `1.2026.6` native Linux amd64 | Derived architecture SVG rendering only | ADR-0003, ADR-0009 and `tooling/architecture_model.py` |
| Documentation font input | DejaVu Fonts `2.37` | Canonical derived-diagram font metrics | ADR-0003 and `tooling/domain_diagrams.py` |
| Diagram layout | Smetana | Derived PlantUML layout without Graphviz | ADR-0003 and `tooling/domain_diagrams.py` |

## Python support

The package requires Python 3.11 or newer.

Normal pull requests targeting `development` are validated locally and do not
run GitHub Actions. The remote `Agentic CI` release gate validates both Python
3.11 and Python 3.13 in the required `Validate generator` job for pull requests
targeting `production`.

## Architecture model and rendering

The canonical semantic architecture model is:

```text
docs/architecture/workspace.dsl
```

Repository-owned validation/export uses Structurizr vNext `2026.06.28` through
the official image identity:

```text
tag:    structurizr/structurizr:2026.06.28-noble
digest: structurizr/structurizr@sha256:b5140a2a783b0cc780fe4b54dcfeecb565ddd5fce5a578e7ff600b78ad0cc03a
os:     linux
arch:   amd64
```

`uv run architecture-model prepare` explicitly acquires the exact
content-addressed image and the retained pinned PlantUML/DejaVu renderer inputs.
`uv run architecture-model check` validates with Docker networking disabled and
does not implicitly resolve another image or remote architecture dependency.

Docker and Structurizr are development/documentation toolchain dependencies for
this architecture-model workflow. They are not compiler-core, product-runtime
or generated-target dependencies. Java is contained inside the accepted
Structurizr image and is not a required host/compiler dependency.

Stakeholder SVGs are derived through deterministic Structurizr PlantUML export
and the retained PlantUML `1.2026.6`/Smetana/DejaVu `2.37` renderer contract.
Exported `.puml` files are ephemeral and are not repository authority.

## Generated targets

`vscode-copilot` and `opencode` are supported output targets. They are not
implementation dependencies of the compiler core.

Adding another target or mandatory technology requires accepted scope and the
technology-admission process in `docs/governance.md`.

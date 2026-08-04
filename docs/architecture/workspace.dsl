workspace "Agentic Workflow Generator" "Stable v1 software architecture" {
    !identifiers hierarchical
    !impliedRelationships false

    model {
        contributor = person "Contributor" "Develops and operates the compiler locally."

        awg = softwareSystem "Agentic Workflow Generator" "Deterministic compiler for validated agentic software-delivery configurations." {
            delivery = container "Delivery interfaces" "Parse interaction and render diagnostics." "Python CLI"
            registry = container "Registry input and validation" "Load external registry representation and produce validated typed input." "Python"
            application = container "Application orchestration" "Coordinate accepted use cases and transactional operations." "Python"
            compiler = container "Deterministic compiler core" "Resolve the sole canonical CompiledComposition." "Python"
            targets = container "Target rendering" "Translate canonical compiled semantics into accepted target representations." "Python"
            infrastructure = container "Materialization and infrastructure" "Own filesystem, hashing, process effects, and transactional materialization." "Python"
        }

        vscode = softwareSystem "VS Code Copilot" "Supported non-owned target coding-agent framework."
        opencode = softwareSystem "OpenCode" "Supported non-owned target coding-agent framework."

        contributor -> awg "Uses locally"
        awg -> vscode "Generates configuration for"
        awg -> opencode "Generates configuration for"

        contributor -> awg.delivery "Invokes"
        awg.delivery -> awg.application "Invokes accepted use cases"
        awg.application -> awg.registry "Loads validated typed compiler input"
        awg.application -> awg.compiler "Requests canonical compilation"
        awg.application -> awg.targets "Supplies canonical CompiledComposition for rendering"
        awg.application -> awg.infrastructure "Coordinates transactional effects"
        awg.targets -> awg.infrastructure "Provides target materialization plans"
        awg.targets -> vscode "Materializes target-specific configuration"
        awg.targets -> opencode "Materializes target-specific configuration"
    }

    views {
        systemContext awg "SystemContext" "Agentic Workflow Generator in its local product context." {
            include contributor awg vscode opencode
            autoLayout lr
        }

        container awg "CompilerResponsibilities" "Stable responsibilities and dependency directions inside the modular monolith." {
            include contributor
            include awg.delivery awg.registry awg.application awg.compiler awg.targets awg.infrastructure
            include vscode opencode
            autoLayout lr
        }

        styles {
            element "Person" {
                shape Person
            }
            element "Software System" {
                shape RoundedBox
            }
            element "Container" {
                shape RoundedBox
            }
        }
    }
}

# Projektstatus — `agentic-workflow-generator`

Opdateret: 24. juli 2026

Denne fil er projektets autoritative status og roadmap. Den skal kun indeholde den aktuelle tilstand, afsluttede hovedleverancer, kendte mangler og næste prioriterede arbejde.

## Slutmål

`agentic-workflow-generator` skal være en deterministisk, fail-fast compiler, der kan omsætte en valideret og genanvendelig registry-komposition til et komplet, target-specifikt agentisk udviklingsmiljø.

En bruger skal kunne vælge et setup eller et bundle og uden manuel efterredigering få genereret agenter, skills, workflows, permissions, handoffs, artifact-kontrakter og targetkonfiguration, som er konsistente med hinanden og kan anvendes direkte i det valgte framework.

Projektet betragtes som færdigt, når følgende er opfyldt:

* Registry-modellen understøtter genanvendelige agentprofiler, konkrete agent-instances, role bindings, separation policies, capabilities, skills, artifact contracts, workflows, permission-profiler og target adapters.
* Den samme registry kan sammensætte både kompakte generalistsetups og specialiserede teams uden at svække sikkerhedsinvarianter eller kræve duplikerede agentdefinitioner.
* Setup- og bundlekompositionen ejer alle konkrete runtimevalg, herunder agent-instances, roller, skills, capabilities, permissions, artifacts og krav om separation of duties.
* Alle workflows er fail-closed og har entydige state owners, controller-binding, transitions, gates, evidenskrav, `BLOCKED`-routing samt definerede retry- og eskalationsgrænser.
* Artifact contracts kan validere status, provenance, revision, inputreferencer og reproducerbar evidens ved workflow-gates.
* Genereret output bevarer den fulde semantik fra registryet og er gyldigt, konsistent og operationelt anvendeligt for hvert understøttet target.
* Init, resolution, generation, lockfile og manifest er deterministiske, idempotente og byte-identiske ved gentaget kørsel med samme input.
* Ugyldige registries, usikre kompositioner, manglende bindings og outputdrift afvises eksplicit uden fallback eller silent degradation.
* Alle registrerede setups kan initialiseres og genereres fra et tomt, isoleret consumer-repository og bestå schema-, semantic-, compatibility-, runtime- og negative-gate-tests.
* Nye agents, skills, workflows, artifacts, setups, bundles, profiles og targets kan tilføjes gennem dokumenterede kontrakter uden ændringer i compilerens kerne, medmindre et nyt domænekoncept introduceres.
* Dokumentation, schemas, validators, genereret output og `project-status.md` beskriver den samme implementerede model.

Projektets mål er at generere og validere agentiske udviklingsmiljøer. Det er ikke i sig selv en modelhost, en autonom runtime-orchestrator eller en erstatning for de frameworks, som outputtet genereres til.

## Aktuel status

Projektet fungerer som en deterministisk og fail-fast compiler:

~~~text
registry
→ setup eller bundle
→ agentic.json
→ resolution
→ lockfile
→ target-output
→ output manifest
→ validering
~~~

### Registry

~~~text
Agents:          8
Skills:         10
Capabilities:   21
Artifacts:       7
Workflows:       4
Profiles:        4
Bundles:         4
Setups:          4
Targets:         2
~~~

Understøttede targets:

* OpenCode
* VS Code Copilot

Registrerede setups:

* `ai-application-greenfield`
* `lean-delivery-greenfield`
* `orchestrated-delivery-greenfield`
* `review-heavy-delivery-greenfield`

## Afsluttet

### Milepæl 1 — Guided init

Milepæl 1 er implementeret, valideret og pushed.

Færdige funktioner:

* interaktivt `init --guided`
* deterministisk `--guided --setup`
* answer overrides
* dry-run
* back-navigation
* cancellation uden filændringer
* transaktionel rollback
* PTY-regressionstests
* modulopdelt init-implementering
* fire reelle setups
* isoleret clean-consumer end-to-end-test

### Milepæl 2 — Første vertical slice

`ai-application` er implementeret med:

* `AIEvaluator`
* `ai-evaluation`
* `AIEvaluationReport`
* AI-profile
* AI-bundle
* AI-workflow
* AI-guided setup

### Target framework-kompatibilitet

Framework-auditten er implementeret og committed som:

~~~text
8e13da3 Validate target framework compatibility
~~~

Færdige forbedringer omfatter:

* gyldigt OpenCode-output
* OpenCode primary/subagent-topologi
* validerede OpenCode-permissions
* validerede Copilot-tools og native handoffs
* deterministisk skill-materialisering
* target compatibility-validator
* OpenCode runtime parsing
* runtime context eksplicit deaktiveret indtil senere milepæl

## Aktuel validering

Følgende består:

~~~text
agentic-gen.sh all
  PASS
  10 skills
  21 capability providers
  8 agent profiles
  43 registry files

agentic-gen.sh test-isolated-e2e
  PASS for alle 4 setups
  222 kumulative deterministiske tracked files

agentic-gen.sh test-target-runtime-e2e
  PASS for alle 4 setups
  OpenCode runtime parser alle setups

agentic-gen.sh test-negative
  PASS: 373 negative gate tests

agentic-gen.sh validate-manifest
  PASS: 2 targets og 53 genererede filer

agentic-gen.sh doctor-strict
  PASS
  PASS: 373 negative gate tests
  PASS: Working tree is clean
~~~

OpenCode 1.17.10 parser config, agents og skills for alle fire isolerede setups.

Gentaget init og generation er byte-identisk.

## Aktuel repositorytilstand

Registry-hardening-fasen er committed og pushed til `main`:

~~~text
79bfe7c Harden registry skills and document agent instance model
~~~

Post-commit `doctor-strict` består med alle 373 negative gate-tests, og working tree var ren ved push.

## Registry-audit — vigtigste fund

Compiler- og validatorinfrastrukturen er stærk, men registry-indholdet er fortsat et MVP.

### Agents og skills

* `mvp-core-capabilities` er fjernet uden fallback.
* 10 fokuserede skills leverer alle 21 registrerede capabilities med én entydig provider per capability.
* Requirements, Architecture, Implementation, Test, QA, Security, AI-evaluering, code review og workflow-routing har konkrete arbejdsmetoder og evidenskontrakter.
* Alle skill-poster bruger rådgivende `recommendedAgents`; feltet begrænser ikke kompositionen.
* Skill-afhængigheder udtrykkes med `requiresCapabilities` og valideres mod registrerede capability-providers.
* Skill-validatoren afviser ugyldige typer, tomme værdier, dubletter, manglende agent- og capability-referencer samt selvafhængighed.
* CodeReviewer må ikke eje routing, og Orchestratorens routing er fail-closed.

### Artifacts

Artifact contracts validerer struktur og headings, men mangler blandt andet:

* statusafhængige evidenskrav
* provenance og revision
* input-artifact-referencer
* reproducerbar evidens
* validerbar handoff- eller dispositionssemantik

### Resterende kompositionslåse

Skill-metadata er nu komponerbare, men den nuværende agent-, bundle-, workflow- og gate-model indeholder fortsat låse, som begrænser små og generaliserede setups:
* Agentens statiske `capabilities` kopieres til enhver materialiseret instans.
* Bundle-validatoren kræver, at alle capabilities på en inkluderet agent dækkes af bundle-skills.
* Resolveren matcher capabilities mod hele skill-registryet og ikke eksplicit kun mod bundlets valgte skills.
* Workflow-gates arver automatisk alle capabilities fra agentdefinitionen.
* En gated agent skal aktuelt producere præcis ét statisk artifact.
* `defaultPermissionProfile` kopieres statisk fra agenten og kan blokere en anden opgavetype.
* Statiske `mustNot`-regler kan kollidere med setup-specifikke roller og skills.

Konsekvensen er, at en specialiseret agentdefinition ikke uden videre kan genbruges som generalist i et mindre setup.

Følgende sikkerhedsinvarianter skal fortsat være hårde:

* fail-closed workflowudførelse
* kun validerede og entydige transitions
* obligatoriske artifacts og evidens ved gates
* eksplicit separation of duties, når et setup kræver uafhængig kontrol
* ingen implicit fallback eller selvopfundne routes

### Workflows

Workflowmodellen mangler blandt andet:

* eksplicit `BLOCKED`-routing
* entydig Orchestrator/controller-semantik
* retry- og eskalationsgrænser
* artifact-invalidation efter ændringer
* klar test-evidens i review-heavy-flowet
* klar execution-model for AI-evaluering

### Profiles og setups

* Den generelle orchestrated-bundle bruger den domænespecifikke `microservice-platform`-profil.
* `microservice-platform` beskriver ikke alle nødvendige capabilities.
* Flere setupvalg ændrer ikke den materialiserede komposition.
* `orchestrated-delivery-greenfield` indeholder forældet review-heavy-tekst.
* Library-valget materialiserer fortsat microservice-profilen.
* Setupkomposition duplikeres flere steder og kan drive.

### Targetmaterialisering

* Agenternes `responsibilities` forsvinder før targetgenerering.
* Generiske outputkrav matcher ikke de artifact-specifikke kontrakter.
* OpenCode materialiserer ikke den fulde workflow-routing til runtimefilerne.
* Copilot mangler eksplicitte `BLOCKED`-handoffs.
* TestRunner-permissions er forskellige mellem targets.
* Profile- og workflowidentitet bruges inkonsistent.

## Beslutninger

* Nye domain-oriented setups er midlertidigt sat på pause.
* `data-pipeline` implementeres først efter registry-hardening.
* `mvp-core-capabilities` er fjernet uden fallback.
* En capability betragtes kun som dækket, når dens skill har en reel arbejdsmetode og evidenskontrakt.
* Skills er komponerbare capability-providers og må ikke som standard hardlåses til bestemte agenter.
* Agentdefinitioner er genanvendelige standardprofiler, ikke komplette uforanderlige runtimeinstanser.
* `recommendedAgents` må kun være rådgivende metadata.
* Setup- og bundlekompositionen skal eje konkrete agent-instances, role bindings, capabilities, skills, instance-level permissions, artifacts og rollegrænser.
* Alle agenter skal principielt kunne få alle skills, når en valideret komposition tildeler dem.
* Hårde begrænsninger reserveres til eksplicitte sikkerhedsinvarianter.
* Chen-målmodellen i `docs/diagrams/agentic-domain-model-chen.puml` er autoritativ for entity boundaries og konceptuelle relationer.
* `AgentProfile`, `AgentInstance`, `RoleBinding` og `SeparationPolicy` skal være adskilte koncepter.
* En agent-instance må bindes til flere workflowroller i kompakte setups.
* Hver agent-instance skal have præcis én effektiv permission-profil.
* Hver ikke-terminal workflow-state skal have præcis én state-owner-binding.
* Hvert workflow skal have præcis én controller-binding uden state- eller gate-ejerskab.
* Uafhængighed skal håndhæves gennem eksplicitte separation policies, ikke globale agentnavne-locks.
* Skill-afhængigheder udtrykkes gennem `requiresCapabilities` og valideres mod registrerede capability-providers.
* Profiles må anbefale og erklære kompatible workflows; bundlet vælger det effektive workflow.
* Strukturel framework-kompatibilitet må ikke beskrives som fuld operationel runtime-kompatibilitet.

## Prioriteret arbejde

### Fase 1 — Skills, agents og kompositionsbindings

Afsluttet:

* opdel de 13 placeholder-capabilities i fokuserede skills
* ret agenternes responsibilities, routinggrænser og centrale `mustNot`-regler
* fjern `mvp-core-capabilities`
* erstat `allowedAgents` med rådgivende `recommendedAgents`
* erstat konkrete skill-afhængigheder med `requiresCapabilities`
* tilføj semantisk validering og negative gates for de nye skillfelter

Resterende:

* adskil agentstandarder fra setup-specifikke capability- og skill-bindings
* bind én effektiv permission-profil per agent-instance og artifact-ansvar per workflowrolle
* valider, at generalist- og specialistsetups kan bruge samme registry

### Fase 2 — Artifact contracts

* tilføj provenance og revision
* tilføj statusafhængige invariants
* tilføj reproducerbare evidenskrav
* definer artifact-specifik statussemantik

### Fase 3 — Workflows

* implementér `BLOCKED`-routing
* afklar central eller distribueret routing
* tilføj retry- og eskalationspolitik
* implementér artifact-invalidation
* ret review-heavy- og AI-evalueringsflow

### Fase 4 — Profiles, bundles og setups

* adskil generic og microservice profiles
* ret capability completeness
* fjern stale og placebo-baserede setupvalg
* reducer duplikeret setupkomposition

### Fase 5 — Targetmaterialisering

* bevar agent-responsibilities
* generér artifact-specifikke outputkrav
* materialisér fuld routing og `BLOCKED`
* harmonisér permissions på tværs af targets
* ret profile- og workflowidentitet

### Fase 6 — Dokumentation og afslutning

* opdatér `registry/README.md`
* opdatér hoved-README
* opdatér relevante udviklerguides
* regenerér lockfile, targets og manifest
* kør fuld validering
* commit og push

## Næste konkrete opgave

Design og implementér konkrete agent-instances, state-owner- og controller-bindings samt eksplicit binding af capabilities, skills og producerede artifacts.

Bindingen skal understøtte både specialiserede teams og kompakte generalistsetups uden at svække fail-closed gates, evidenskrav eller eksplicit separation of duties.

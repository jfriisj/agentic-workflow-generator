# Samlet status for `agentic-workflow-generator`

## Den korte vurdering

Projektet har nu en **meget stærk teknisk kerne**. Det er ikke længere bare en samling agent-prompts; det fungerer som en deterministisk compiler:

```text
registry
  → setup/bundle
  → agentic.json
  → resolution
  → lockfile
  → target-specifik generering
  → manifest
  → validering og negative gates
```

Det officielle projektmål er netop at omsætte et deklarativt registry af agents, skills, workflows, bundles, artifacts, gates og target adapters til platformsspecifik konfiguration på en reproducerbar og fail-fast måde. ([GitHub][1])

Det seneste checkpoint er:

```text
14e5282 Add interactive guided init PTY tests
```

Og den aktuelle tilstand er:

* `doctor-strict` består
* alle **354 negative gates** består
* working tree er ren
* `main` er pushed til GitHub
* både interaktiv og ikke-interaktiv initialisering virker

---

# 1. Det oprindelige mål

Projektets vision er at gøre agentiske software-workflows:

* deklarative,
* platformuafhængige,
* reproducerbare,
* deterministiske,
* validerbare,
* fail-fast.

I stedet for manuelt at vedligeholde forskellige agentfiler til Copilot, OpenCode og fremtidige platforme, definerer man én canonical model og genererer målplatformenes filer derfra. Registry, bundle, config, resolution, lockfile og output manifest udgør allerede denne compiler-lignende pipeline. ([GitHub][2])

Den senere vision blev udvidet fra blot at generere agentfiler til en **project-shaping wizard**:

```text
brugerens projektintention
  → setup profile
  → anbefalet workflow
  → agents og skills
  → permissions og MCP
  → target-specifik konfiguration
```

Projektet er bevidst greenfield-first: `init --guided` skal hjælpe med at forme et nyt projekts arbejdsform, mens analyse af eksisterende projekter kommer senere som et separat brownfield-flow. 

---

# 2. Hvad der er færdigt

## A. Canonical domænemodel og registry

Der findes nu registry-typer for:

* agents,
* skills,
* workflows,
* profiles,
* bundles,
* artifacts,
* targets,
* setups.

Alle centrale registry-filer har både strukturel og semantisk validering.

Den aktuelle sammensætning indeholder:

* 7 agents,
* 4 skill-directories,
* 18 capabilities,
* 1 workflow,
* 1 profile,
* 1 bundle,
* 6 artifact contracts,
* 2 target adapters,
* 1 guided setup.

### Agents

Den eksisterende orchestrated-delivery-bundle indeholder:

* Requirements
* Architect
* Implementer
* CodeReviewer
* TestRunner
* QA
* Orchestrator

Bundle-sammensætningen er valideret som en samlet deployerbar enhed, ikke blot som løse referencer. Workflow-states skal være dækket af agents, capabilities skal dækkes af skills, producerede artifacts skal være med i bundlen, og targets skal passe til deres adapters. ([GitHub][1])

---

## B. Workflow-motorens deklarative model

Workflow-registryet understøtter blandt andet:

* start-state,
* terminal states,
* transitions,
* transition events,
* agents per state,
* gates,
* fail-closed routing,
* reachability-validering.

Validatorerne stopper blandt andet:

* ukendte states,
* unreachable states,
* terminal states med outgoing transitions,
* manglende agents,
* manglende gates,
* ugyldige transition-events,
* gates uden korrekte artifact-statusser.

Det betyder, at workflowet ikke blot er dokumentation. Det er en maskinvalideret state machine.

---

## C. Artifact contracts og gate-binding

Agents kan deklarere de artifacts, de producerer, eksempelvis:

* Requirements
* Architecture
* ImplementationReport
* CodeReview
* TestReport
* QAReport

Artifact contracts kan definere:

* type,
* path pattern,
* tilladte statuser,
* obligatoriske headings,
* JSON Schema.

Workflow-gates er bundet til artifacts og deres statuser. En gate kan derfor ikke godkendes på baggrund af en løs tekststreng, hvis det krævede artifact eller den krævede status mangler.

Det er en af projektets stærkeste egenskaber: der er en egentlig kontrakt mellem workflow-state, agent-output og transition.

---

## D. Capability- og skill-modellen

Agents deklarerer capabilities, mens skills leverer capabilities.

Systemet validerer:

* manglende skill coverage,
* ubrugte capabilities,
* dublerede capability-providers,
* agents der kræver capabilities, ingen skill leverer,
* capabilities der dækkes af flere skills uden tilladelse.

Den nuværende konfiguration har:

```text
Agent capabilities: 18
Skill capabilities: 18

Missing: none
Unused: none
Duplicate: none
```

---

## E. Bundle composition

Bundlen fungerer nu som en komplet deployerbar sammensætning af:

```text
workflow
profile
agents
skills
artifacts
targets
```

Der valideres blandt andet:

* alle workflow-agents er inkluderet,
* transitions holder sig inden for workflowet,
* alle agent-capabilities er dækket,
* producerede artifacts er inkluderet,
* target adapters matcher,
* profile og workflow matcher.

Det var en vigtig milepæl, fordi bundlen dermed er mere end en liste over filnavne.

---

## F. Resolver og resolution output

`.agentic/agentic.json` bliver resolved mod registryet.

Resolution-outputtet indeholder blandt andet:

* resolved agents,
* resolved skills og capabilities,
* workflow-state og transitions,
* targets og adapter paths,
* producerede artifact bindings,
* projektprofil,
* manglende dependencies,
* summary counts.

Resolution-filen valideres både strukturelt og semantisk mod de oprindelige registries.

---

## G. Deterministisk lockfile

`.agentic/agentic-lock.json` registrerer:

* alle relevante inputfiler,
* filstørrelser,
* SHA-256-hashes,
* samlet content hash,
* samlet antal filer.

Lockfilen opdager:

* ændrede registry-filer,
* manglende inputs,
* nye utracked registry-inputs,
* hash-drift,
* størrelse-drift,
* forkert file count.

Den seneste pipeline sporer 69 inputfiler.

---

## H. Output manifest og fil-ejerskab

Output manifestet registrerer:

* aktiv bundle,
* targets,
* target adapters,
* owned paths,
* genererede filer,
* byte-størrelser,
* SHA-256-hashes,
* summary counts.

Det validerer blandt andet:

* manglende genererede filer,
* ændret indhold,
* forkert byte-størrelse,
* forkert hash,
* absolutte eller usikre paths,
* filer uden for adapterens owned paths,
* unmanaged genererede filer,
* drift mellem manifest og bundle registry.

Projektet kan også opdage og rydde unmanaged generated output via dry-run og apply.

README beskriver output manifestet og dets ejerskabsmodel som en central del af pipeline-kontrakten. ([GitHub][2])

---

## I. Target-generering

Projektet understøtter aktuelt:

* VS Code Copilot
* OpenCode

Der genereres blandt andet:

```text
.github/agents/*
.github/skills/*
.github/copilot-instructions.md

.opencode/agents/*
.opencode/skills/*
AGENTS.md
opencode.json
```

Target adapters definerer platformnavn, beskrivelse og owned paths.

Der findes både strukturel og semantisk validering af target adapters.

---

## J. Init fra bundle

Det deterministiske init-flow fungerer:

```bash
scripts/agentic/agentic-gen.sh init \
  --bundle orchestrated-delivery
```

Det materialiserer den aktive `.agentic/agentic.json` fra den registrerede bundle.

Idempotency-validatoren beviser, at samme bundle giver samme output ved gentagen kørsel.

---

## K. Guided setup foundation

Dette er den milepæl, vi netop har afsluttet.

Der findes nu:

```text
registry/setups/
.agentic/schemas/registry/setup.schema.json
.agentic/setup-profile.json
scripts/agentic/validate-setup-registry.py
scripts/agentic/validate-setup-profile.py
```

Setup-modellen understøtter:

* spørgsmål,
* options,
* recommended choices,
* compatible choices,
* blocked choices,
* forklaringer,
* anbefalede agents,
* anbefalede skills,
* anbefalede artifacts,
* anbefalede targets,
* default bundle.

Det matcher den tidligere beslutning om, at guided init skal være en deterministisk anbefalingsmotor med `recommended`, `compatible` og `blocked`, ikke et LLM-baseret eller tilfældigt valg. 

---

## L. Ikke-interaktiv guided init

Det deterministiske setup-flow fungerer:

```bash
scripts/agentic/agentic-gen.sh init \
  --guided \
  --setup orchestrated-delivery-greenfield
```

Overrides kan gives eksplicit:

```bash
--answer target-platforms=opencode-only
```

Det er vigtigt for:

* CI,
* scripting,
* reproducerbarhed,
* idempotency-tests.

`--guided --setup` kræver ikke en terminal og ændrer ikke sin adfærd afhængigt af brugerinput.

---

## M. Interaktiv guided init

Det nye flow fungerer nu:

```bash
scripts/agentic/agentic-gen.sh init --guided
```

Det:

1. kræver en rigtig TTY,
2. validerer setup registry,
3. viser registrerede setups,
4. viser spørgsmål og options,
5. viser klassifikation og forklaring,
6. anvender recommended defaults,
7. materialiserer setup-profile,
8. viser den endelige plan,
9. kræver eksplicit bekræftelse,
10. skriver config og setup-profile.

Interaktiviteten er adapteren oven på den samme deterministiske setup-model; den duplikerer ikke anbefalingslogikken. Implementeringen bevarer også det eksisterende ikke-interaktive flow. 

### Transaktionel skrivning

Ved fejl under validering bliver de tidligere versioner af:

```text
.agentic/setup-profile.json
.agentic/agentic.json
```

gendannet.

Ved annullering bliver der ikke skrevet noget.

### Automatiske pseudo-TTY-tests

Den interaktive dialog testes nu automatisk med Python-standardbibliotekets PTY-funktionalitet:

* default happy path,
* plan generation,
* confirmation,
* korrekt target selection,
* cancellation,
* byte-for-byte uændrede filer,
* uændrede modification timestamps.

Der blev ikke tilføjet en ekstern dependency som `pexpect`.

---

## N. Kvalitetssystemet

Projektet har nu:

* syntakschecks,
* JSON-validering,
* JSON Schema-validering,
* referencevalidering,
* semantiske validators,
* idempotency-tests,
* drift detection,
* output ownership,
* negative gates,
* `verify-quiet`,
* `doctor`,
* `doctor-strict`,
* Git hooks,
* CI.

Den negative suite har nu **354 tests**, som bevidst ødelægger kontrakter og beviser, at systemet fejler lukket.

Det er meget stærkere end blot at teste happy path.

---

# 3. Hvad der kun er delvist færdigt

## A. Guided init har kun ét setup

Der findes kun:

```text
orchestrated-delivery-greenfield
```

Det betyder, at infrastrukturen er færdig, men anbefalingsmotorens faglige bredde endnu er meget lille.

De næste naturlige setups er eksempelvis:

```text
ai-application
data-pipeline
web-api
library
cli-tool
frontend-application
documentation-project
```

Men de bør ikke blot være kopier af samme bundle. De bør have reelt forskellige:

* workflows,
* profiles,
* agents,
* skills,
* artifacts,
* target recommendations.

---

## B. Anbefalingsmodellen er stadig første generation

`recommended`, `compatible` og `blocked` findes.

Men den fulde vision var, at tidligere valg påvirker senere anbefalinger:

```text
project type
  → architecture
  → workflow
  → agents
  → skills
  → MCP
  → permissions
```

Det nuværende fundament kan materialisere recommendations fra options, men der mangler en rigere regelmodel til kombinationer af flere tidligere svar.

Eksempel:

```text
AI application + event-driven
```

bør potentielt give en anden anbefaling end:

```text
AI application + layered architecture
```

Dette er ikke nødvendigvis nødvendigt til første MVP, men det er en del af den fulde vision.

---

## C. Guided UX kan forbedres

Nuværende mindre UX-mangler:

* `back` fra første spørgsmål bør gå tilbage til setup-valget,
* der mangler muligvis en ren `--dry-run`,
* der mangler en bedre samlet forklaring af konsekvensen ved compatible overrides,
* der mangler mulighed for at eksportere eller vise planen uden at skrive,
* flere setups kræver bedre navigation og filtrering.

Fail-fast-adfærden ved ugyldigt input bør dog bevares. Der bør ikke indføres skjult fallback eller automatisk korrektion.

---

## D. Dokumentationen er bagefter koden

README viser stadig primært bundle-flowet:

```bash
init --bundle orchestrated-delivery
```

Den dokumenterer ikke tydeligt:

```bash
init --guided
init --guided --setup ...
--answer ...
setup-profile.json
recommended / compatible / blocked
```

README beskriver de eksisterende compiler- og validatorfunktioner godt, men guided init-milen er endnu ikke afspejlet i quickstart eller command-listen. ([GitHub][2])

Det er nu en reel dokumentationsdrift, selv om generated-output drift er grøn.

---

## E. `init-from-bundle.py` vokser for meget

Guided dialog, setup-materialisering, filskrivning, rollback, argument parsing og bundle init ligger nu i samme fil.

Det fungerer, men filen er blevet stor.

Før vi føjer MCP, brownfield discovery og flere setup-typer til, bør ansvaret opdeles, eksempelvis:

```text
init_from_bundle.py
guided_init.py
setup_materializer.py
transactional_write.py
```

Det bør ske uden at ændre den offentlige CLI eller anbefalingsmodellen.

---

## F. Test-harnesset er stort

`test-negative-gates.py` er nu meget omfattende.

Det er stadig værdifuldt som samlet fail-closed suite, men på længere sigt bør hjælpefunktioner og domænespecifikke grupper opdeles:

```text
tests/negative/
  test_agent_registry.py
  test_workflow_registry.py
  test_bundle_registry.py
  test_setup_registry.py
  test_resolution.py
  test_output_manifest.py
  test_guided_init.py
```

Den samlede kommando kan stadig aggregere alle tests.

Dette er vedligeholdelsesarbejde, ikke en funktionel blocker.

---

# 4. Hvad der mangler i den fulde vision

## A. MCP registry

Dette er den største manglende domænekomponent.

Der mangler eksempelvis:

```text
registry/mcp-servers/
registry/mcp-capabilities/
registry/permission-profiles/
```

MCP-modellen skal beskrive:

* server,
* capabilities,
* operations,
* safety level,
* required secrets,
* read/write/destructive,
* confirmation requirements,
* hvilke targets der understøtter den.

Den tidligere roadmap placerede MCP efter guided setup, netop for at det kunne bygges oven på en stabil setup-profile og bundle-model. 

---

## B. Skill → MCP requirements

Skills skal kunne deklarere eksterne runtime-behov.

Eksempel:

```json
{
  "name": "github-code-review",
  "requiresMcpCapabilities": [
    "github.pull_requests.read",
    "github.pull_requests.comment"
  ]
}
```

Validatoren skal stoppe en bundle, hvis en skill kræver en capability, som ingen valgt MCP-server leverer.

---

## C. Agent permissions og sikkerhed

Der mangler en formel permission-model for hver agent.

Eksempel:

```text
Requirements:
  filesystem.read

Implementer:
  filesystem.read
  filesystem.write
  git.diff

CodeReviewer:
  filesystem.read
  git.diff
  github.pull_requests.read

Orchestrator:
  workflow.transition
```

Det skal være umuligt at tildele destruktive handlinger til agents, der ikke må have dem.

Eksempel på ønsket fail-fast-adfærd:

```text
FAIL: CodeReviewer requests github.pull_requests.merge,
but its permission profile does not allow destructive actions.
```

---

## D. Bundle MCP completeness

Bundle-validatoren skal udvides med:

```text
agent requirements
  → skill requirements
  → MCP capabilities
  → selected MCP servers
  → permission profile
  → target support
```

Hele kæden skal være dækket, før en bundle kan materialiseres.

---

## E. Per-agent runtime context

De genererede agentfiler skal på sigt indeholde mere end prompts og skills.

De skal også kunne indeholde:

* tilladte tools,
* MCP-serveradgang,
* permission scope,
* artifact paths,
* workflow-state,
* gate-kontrakter,
* confirmation policy,
* secret requirements.

Det vil gøre hver generated agent til en egentlig runtime-konfiguration.

---

## F. Flere workflows og profiles

Der findes kun ét workflow og én central profile.

For at systemet reelt kan anbefale forskellige setups, mangler eksempelvis:

### Workflows

```text
simple-delivery
test-first-delivery
review-heavy-delivery
security-gated-delivery
documentation-first
data-pipeline-delivery
ai-evaluation-delivery
```

### Profiles

```text
web-api
ai-application
data-pipeline
library
cli-tool
microservice-platform
```

Uden flere workflows og profiles vil flere setups hovedsageligt blive kosmetiske varianter.

---

## G. Flere agents og skills

Det fremtidige registry kan få behov for:

### Agents

```text
SecurityReviewer
DevOps
DataEngineer
MLEngineer
AIEvaluator
Documentation
ReleaseManager
```

### Skills

```text
security-review
containerization
kubernetes
github-workflows
api-design
database-migration
data-quality
model-evaluation
prompt-evaluation
observability
release-management
```

Disse bør kun tilføjes, når et konkret setup eller workflow kræver dem.

---

## H. Brownfield project discovery

Der mangler stadig det senere flow:

```bash
scripts/agentic/agentic-gen.sh discover
scripts/agentic/agentic-gen.sh init --from-project
```

Discovery skal kunne analysere et eksisterende repository:

* sprog,
* frameworks,
* build-system,
* test-framework,
* CI,
* container setup,
* arkitekturindikatorer,
* eksisterende agentfiler,
* dokumentation.

Resultatet bør være en deklarativ discovery-report, ikke direkte ukontrolleret ændring af config.

Den oprindelige roadmap placerer brownfield discovery efter MCP og runtime context. 

---

## I. Optional project scaffolding

Den langsigtede vision kan generere:

```text
src/
tests/
docs/
.github/workflows/
Makefile
pyproject.toml
package.json
pom.xml
```

Men dette bør fortsat ligge sent i roadmapet.

Første produktversion bør være en **agentic setup compiler**, ikke en generel application generator.

---

## J. Flere target adapters

Aktuelt understøttes kun Copilot og OpenCode. ([GitHub][1])

Fremtidige targets kan være:

```text
Cursor
Claude Code
Claude Desktop
custom runtime
generic Markdown
```

Der bør først tilføjes en ny target, når:

* platformens config-format er stabilt,
* owned paths kan defineres,
* output kan valideres,
* targetet har en rigtig use case.

---

## K. Produktdistribution

Repoet har endnu ingen publicerede releases eller packages. ([GitHub][1])

Der mangler derfor en egentlig installationshistorie:

```text
curl installer
pipx install
package release
standalone archive
versioned GitHub release
```

Før dette bør der være:

* semantisk versionering,
* changelog,
* release notes,
* kompatibilitetspolitik for schemas,
* migrationsstrategi.

---

## L. Eksterne end-to-end eksempelprojekter

Projektet tester sig selv meget grundigt, men der mangler et eller flere uafhængige eksempelrepositories, der bruger generatoren som forbruger.

Eksempel:

```text
examples/python-api/
examples/ai-application/
examples/data-pipeline/
```

En reel acceptance test bør være:

```text
tom mappe
  → installer generator
  → init --guided eller deterministic setup
  → generate
  → doctor-strict
  → valid target output
```

Det vil bevise, at generatoren ikke kun virker inde i sit eget repository.

---

# 5. Min vurdering af modenheden

Dette er et skøn, ikke et objektivt måltal.

## Compiler-kernen

**Omkring 85–90 % af en stærk første version**

Det centrale flow fungerer:

```text
registry
→ composition
→ resolution
→ lock
→ generation
→ manifest
→ validation
```

De svære dele omkring determinisme, ejerskab, drift og fail-closed validation er allerede bygget.

## Guided-init MVP

**Omkring 70–75 %**

Fundamentet, det interaktive flow og bruger-/CLI-dokumentationen fungerer, men der mangler:

* flere setups,
* flere workflows/profiles,
* bedre UX,
* ekstern end-to-end fixture.

## Den fulde langsigtede vision

**Omkring 45–55 %**

De største manglende områder er:

* MCP,
* permissions,
* runtime context,
* brownfield discovery,
* flere platforme,
* distribution,
* scaffolding.

Det er ikke et tegn på, at projektet er halvfærdigt teknisk. Det skyldes, at den fulde vision er væsentligt bredere end compiler-kernen.

---

# 6. Anbefalet roadmap herfra

## Milepæl 1 — Gør guided init release-klar

Dette bør være næste fokus, før MCP.

1. ✅ Opdater README og lav `docs/guided-init.md`.
2. ✅ Dokumentér både interactive og deterministic flows.
3. ✅ Tilføj `--dry-run`.
4. Ret `back`-navigationen.
5. Del `init-from-bundle.py` op i mindre moduler.
6. Tilføj mindst to nye reelle setups.
7. Lav en ekstern eller isoleret end-to-end fixture.

**Resultat:** En troværdig `v0.1` som agentic setup compiler.

---

## Milepæl 2 — Udvid setup-domænet

Tilføj først de registry-elementer, der gør setups fagligt forskellige:

```text
ai-application
data-pipeline
web-api
library
```

Tilføj derefter nødvendige:

* profiles,
* workflows,
* agents,
* skills,
* artifacts.

Undgå at lave mange setups, som alle materialiserer samme bundle.

---

## Milepæl 3 — MCP og permission model

Byg i denne rækkefølge:

```text
MCP registry
→ MCP capability schema
→ permission profiles
→ skill MCP requirements
→ agent permission requirements
→ bundle completeness
→ negative gates
```

Ingen generator-output før domænemodellen og validatorerne er grønne.

---

## Milepæl 4 — Per-agent runtime generation

Udvid target adapters, så de kan generere:

* tools,
* MCP config,
* permissions,
* confirmation policies,
* runtime context.

Derefter valideres target-support for alle valgte runtime capabilities.

---

## Milepæl 5 — Brownfield discovery

Byg:

```text
discover
→ discovery-report.json
→ validate discovery report
→ recommended setup
→ init --from-project
```

Discovery bør kun observere og anbefale. Den bør ikke have fallback eller skrive ukontrolleret.

---

## Milepæl 6 — Produktisering

Tilføj:

* versionering,
* changelog,
* release workflow,
* installation,
* migration policy,
* eksempelprojekter,
* udvidelsesdokumentation for nye targets og registry-typer.

---

## Milepæl 7 — Optional scaffolding

Først derefter:

```text
agent setup
+ projektstruktur
+ CI
+ starter code
```

Det bør være et eksplicit tilvalg og ikke standardadfærd.

---

# 7. Den vigtigste konklusion

Projektet mangler ikke længere sit fundament.

Det, der allerede findes, er en ret komplet og usædvanligt grundigt valideret **agentic workflow compiler**.

Den vigtigste risiko nu er ikke manglende validators. Det er at gøre projektet for bredt for hurtigt.

Den mest fornuftige rækkefølge er derfor:

```text
færdiggør guided-init som et brugbart produkt
→ tilføj flere reelle setups
→ byg MCP og permissions
→ byg runtime contexts
→ byg brownfield discovery
→ produktisér og udvid targets
→ overvej scaffolding til sidst
```

Det næste konkrete projektmål bør være:

> **Release-ready Guided Setup v0.1:** En ny bruger skal kunne starte i en tom mappe, vælge et af flere meningsfulde setups og ende med deterministisk, valideret output til Copilot og OpenCode uden manuel redigering.

[1]: https://github.com/jfriisj/agentic-workflow-generator "GitHub - jfriisj/agentic-workflow-generator: Platform-independent generator tool that can translate a declarative agent workflow specification into target-specific agent configurations, skills, gates, validators and runtime contexts for different coding-agent environments. · GitHub"
[2]: https://github.com/jfriisj/agentic-workflow-generator/blob/main/README.md "agentic-workflow-generator/README.md at main · jfriisj/agentic-workflow-generator · GitHub"

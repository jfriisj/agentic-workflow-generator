# ADR-0011: Canonical workflow routing semantics

- Status: Accepted
- Date: 2026-08-11

## Context

ADR-0008 requires the v1 compiler contract to make workflow routing explicit,
deterministic, fail-closed, and preservable by both supported targets.

The current workflow model already establishes:

- one start state;
- one or more terminal states;
- one blocking gate for every non-terminal state;
- explicit transitions with `from`, `to`, and `on`;
- one workflow-controller binding;
- one state-owner binding per non-terminal state;
- one explicit terminal `defaultFailureState`;
- no outgoing transitions from terminal states;
- deterministic validation of duplicate transition events and invalid endpoints;
- transition events constrained by the statuses allowed by gate-required
  artifacts.

Artifact status semantics are already canonical:

- `PASS` requires complete required evidence and no demonstrated applicable
  nonconformance;
- `FAIL` requires demonstrated nonconformance;
- `BLOCKED` requires an unavailable, missing, or unverifiable required
  prerequisite;
- artifact-specific classification remains owned by artifact contracts and the
  producing state-owner role.

ADR-0006 explicitly leaves workflow routing outside artifact classification:
the workflow controller routes an already-produced gate result and does not gain
artifact-status classification authority.

The remaining ambiguity is routing itself.

The registry schema currently accepts any non-empty transition `on` string, while
the current workflows use only `pass` and `fail`. `BLOCKED` is a valid governed
artifact status but has no explicit route in the current workflows.

The current target rendering also exposes routing through worker-facing handoffs.
That representation can let state owners appear to select transitions, and a
non-`pass` transition to a terminal state is currently described as a blocked
outcome even when the actual event is `fail`. Those are semantic-preservation
gaps because routing authority belongs to the workflow controller and `FAIL` is
not `BLOCKED`.

The decision therefore needs to define one canonical routing contract without
introducing workflow execution, retries, escalation, persistence, or a second
policy authority.

## Decision

### Canonical routing result vocabulary

A workflow transition is selected only from one already-classified gate result:

~~~text
PASS
FAIL
BLOCKED
~~~

Registry and active-configuration transition objects keep the existing `on`
member, but its canonical serialized values are exactly:

~~~text
pass
fail
blocked
~~~

The mapping is exact:

~~~text
PASS    -> pass
FAIL    -> fail
BLOCKED -> blocked
~~~

`on` is therefore not an arbitrary event name. It is the serialized workflow
routing form of the already-produced canonical gate result.

The typed domain must represent this with a closed enum/value type rather than
an unconstrained string.

This mapping does not create a second status classifier. Artifact contracts
continue to own status meaning, and the state-owner continues to classify its
governed result. The controller only consumes that result.

### Total deterministic routing for every non-terminal state

Every non-terminal state must declare exactly one outgoing transition for each
canonical gate result:

~~~text
pass
fail
blocked
~~~

Therefore every valid non-terminal state has exactly three routing entries.

For a given source state and gate result:

- zero matching transitions is invalid;
- more than one matching transition is invalid;
- exactly one matching transition is required.

Transition list order has no routing meaning.

Canonical serialization remains deterministic using the existing workflow
transition representation; implementations should use one stable lexical order,
preferably:

~~~text
(source state, gate result, target state)
~~~

No target or runtime consumer may use declaration order as priority.

### Meaning of each route

`pass` means the gate owner has produced a canonical `PASS` result. The
controller follows the unique configured `pass` transition.

`fail` means the gate owner has produced a canonical `FAIL` result. The
controller follows the unique configured `fail` transition. That transition may
lead to:

- an explicitly configured remediation state; or
- a terminal state.

A fail route to a remediation state is an existing workflow transition, not a
retry policy. This ADR does not define retry counts, retry scheduling, or
escalation.

`blocked` means the gate owner has produced a canonical `BLOCKED` result. Every
`blocked` transition must explicitly target the workflow's
`defaultFailureState`.

This makes `BLOCKED` routing explicit and fail-closed without inventing recovery
semantics for unavailable prerequisites.

### `defaultFailureState`

`defaultFailureState` remains a required terminal workflow state.

Its routing meaning is narrow:

- it is the mandatory explicit target of every `blocked` transition;
- a `fail` transition may explicitly target it when the workflow has no
  configured remediation route for that failure;
- a `pass` transition must not target it.

`defaultFailureState` is not an implicit fallback transition.

Missing, ambiguous, malformed, or unsupported routing is a contract error and
must not be hidden by silently routing to `defaultFailureState`.

If an impossible routing condition is nevertheless encountered after validated
compilation, the consumer must stop without transition and surface the routing
failure.

### Controller authority

The workflow-controller binding is the sole owner of routing selection.

The controller owns:

- initial dispatch to the owner of the configured `startState`;
- reading the current workflow state;
- receiving the already-classified gate result;
- selecting the one transition matching `(current state, gate result)`;
- dispatching to the owner of the selected non-terminal target state;
- stopping when the selected target is terminal;
- failing closed when the expected canonical routing information is unavailable
  or inconsistent.

The controller does not own:

- a workflow state;
- a gate;
- artifact production;
- artifact status classification;
- gate evidence evaluation;
- domain-specific review;
- transition invention;
- route priority;
- retry or escalation policy.

The controller must not reinterpret `PASS`, `FAIL`, or `BLOCKED`, and must not
choose a route based on free-form responsibilities, skills, prose, target
features, or artifact type alone.

### State-owner boundary

A state-owner owns its state, gate responsibility, governed artifact production,
and artifact classification.

After producing the canonical gate result, the state-owner returns control and
that result to the workflow controller.

A state-owner must not select or execute the next workflow transition.

Producer-facing target guidance may describe the configured routing table for
context, but it must not grant transition-selection authority to the state
owner.

### Terminal states

Terminal states:

- have no gate;
- have no state-owner binding;
- have no outgoing transitions.

When a selected transition reaches a terminal state, workflow routing stops.

The terminal state name does not reclassify the gate result. For example, a
`fail` transition targeting a terminal state named `Blocked` remains a `FAIL`
route; it must not be described as `BLOCKED`.

### Static compiler boundary

The compiler must prove the static routing contract from validated registry and
composition state.

It can prove:

- every transition endpoint exists;
- terminal states have no outgoing transitions;
- every non-terminal state has exactly one `pass`, one `fail`, and one
  `blocked` transition;
- no other transition event is accepted;
- every `blocked` transition targets `defaultFailureState`;
- no `pass` transition targets `defaultFailureState`;
- `defaultFailureState` is terminal;
- the existing start-state, reachability, and terminal-path invariants;
- exactly one controller binding exists;
- every non-terminal state has exactly one state owner;
- the canonical routing table can be preserved by every enabled target.

The compiler does not:

- execute gates;
- inspect arbitrary produced runtime Markdown to discover status;
- decide artifact status;
- persist workflow state;
- track invocation history;
- execute transitions;
- decide retries or escalation.

A produced runtime result that is missing or cannot be classified under the
accepted artifact contract does not authorize a transition. Existing artifact
semantics require missing required evidence to become `BLOCKED` when no
demonstrated `FAIL` exists; routing begins only after that canonical result
exists.

### Gate aggregation remains outside this decision

This ADR defines routing from one already-produced gate result.

It does not define a new aggregation algorithm for conflicting statuses across
multiple artifacts or evidence sources.

The current accepted workflows continue to use their existing state-owner/gate
responsibility and artifact-status contracts. If a future workflow requires a
new multi-artifact gate-result aggregation rule, that rule requires its own
accepted semantics rather than being inferred by the controller.

This preserves separation from the later workflow test-evidence decision.

### Canonical representation

The existing workflow inside `CompiledComposition` remains the canonical routing
representation.

No second routing graph, policy table, or target-specific route model is added.

The minimum typed contract is:

~~~text
WorkflowTransition
  source
  target
  gate result: PASS | FAIL | BLOCKED
~~~

The external registry and active configuration may keep the existing field name
`on`, serialized as `pass`, `fail`, or `blocked`.

`CompiledComposition.controller_binding` continues to identify the sole routing
owner.

The active configuration must preserve the complete validated transition table
without inference or omission.

### Version consequences for the later implementation

Because the workflow contract is narrowed from arbitrary event strings and
`pass`/`fail` partial routing to a required total `pass`/`fail`/`blocked`
contract:

- advance all four current workflow definitions from `0.2.0` to `0.3.0`;
- advance the active-config schema version from `0.9.0` to `0.10.0`;
- update the workflow registry schema so transition `on` accepts exactly
  `pass`, `fail`, or `blocked`;
- update the active-config schema consistently;
- do not change the generator version solely for this work;
- do not change bundle versions solely because the referenced workflow contract
  evolves, unless implementation also changes bundle-owned source semantics.

Generated active configuration, lockfile provenance, target output, and output
manifest must be regenerated through the normal compiler pipeline.

### Target preservation

Both current targets must preserve the same controller-owned routing contract.

Controller-facing output must expose enough canonical information to determine:

- start state;
- current state;
- gate result vocabulary;
- the unique transition for each `(state, result)` pair;
- terminal states;
- `defaultFailureState`.

State-owner output must make clear that the worker:

- produces/classifies its governed result;
- returns that result to the controller;
- does not choose the next route.

Targets must not:

- attach authoritative next-state selection to state-owner workers;
- infer routes from prose;
- infer routes from artifact type;
- collapse `FAIL` and `BLOCKED`;
- omit a required `blocked` route;
- invent transition priority;
- silently use `defaultFailureState` as fallback;
- invent a target-specific transition.

A target may use target-native handoff constructs only when those constructs
preserve controller ownership. If a target cannot preserve the canonical
routing semantics, rendering must fail explicitly.

## Alternatives considered

### Keep arbitrary transition event strings

Rejected.

The current event-shaped representation permits values that are not canonical
gate results and leaves the relationship between artifact status and routing
implicit. V1 requires a closed fail-closed routing contract.

### Keep only `pass` and `fail` and treat missing evidence as failure

Rejected.

Accepted artifact semantics distinguish `FAIL` from `BLOCKED`. Missing or
unverifiable prerequisites do not become demonstrated nonconformance. Routing
must preserve that distinction.

### Add an implicit `BLOCKED -> defaultFailureState` fallback

Rejected.

An implicit fallback would allow incomplete workflow definitions to appear
valid and would hide missing canonical transitions. `BLOCKED` routing must be
explicit in every non-terminal state.

### Let state owners select their outgoing transitions

Rejected.

Bundle and architecture invariants already assign routing authority to the
workflow controller. Letting workers select routes creates competing routing
authority and makes target behavior dependent on target-specific handoff
mechanics.

### Introduce a generic workflow policy/rules engine

Rejected.

The required v1 semantics are a finite mapping from three canonical gate results
to explicit transitions. A policy engine would add runtime responsibility and a
second interpretation layer without an accepted need.

### Add retry or escalation semantics

Rejected for this decision.

Existing fail routes may return to an earlier remediation state, but the
workflow contains no accepted retry count, timing, escalation, or invalidation
policy. Those concerns remain deferred.

## Consequences

Workflow routing becomes a closed, total, deterministic table over the existing
three canonical artifact/gate outcomes.

`BLOCKED` becomes first-class explicit routing rather than an omitted status or
a synonym for `FAIL`.

The workflow controller becomes enforceably the sole route selector in both
canonical compilation and generated target behavior.

State-owner agents remain responsible for evidence and classification but no
longer appear to own transition execution.

`defaultFailureState` gains one precise fail-closed meaning without becoming a
silent fallback.

The later implementation will change workflow contracts, schemas, validation,
typed routing representation, active configuration, target rendering, all four
current workflow definitions, focused tests, and normal generated output, but
it requires no new runtime, persistence owner, target, technology, policy
engine, retry mechanism, or escalation mechanism.

## Acceptance scenarios

A conforming implementation must satisfy at least these scenarios:

1. `on: pass`, `on: fail`, and `on: blocked` are the only valid transition
   results.
2. Any other transition event is invalid.
3. Every non-terminal state has exactly one transition for each canonical
   result.
4. Missing `pass`, `fail`, or `blocked` routing is invalid.
5. Duplicate routing for one state/result is invalid.
6. Terminal states have no outgoing transitions.
7. Every `blocked` transition targets `defaultFailureState`.
8. `defaultFailureState` is terminal.
9. A `pass` transition to `defaultFailureState` is invalid.
10. A `fail` transition may target an explicit remediation state.
11. A `fail` transition may explicitly target a terminal state.
12. A `FAIL` result remains `FAIL` even when its target terminal state is named
    `Blocked`.
13. A `BLOCKED` result is never converted into `FAIL`.
14. The controller dispatches the configured start state.
15. The controller routes only from the unique configured transition matching
    the current state and already-produced gate result.
16. A state-owner does not gain route-selection authority in either target.
17. Missing or ambiguous routing cannot silently fall back to
    `defaultFailureState`.
18. Both current targets preserve the complete canonical routing table.
19. Target rendering fails if controller-owned routing cannot be preserved.
20. The typed domain uses a closed routing-result type rather than arbitrary
    transition-event strings.
21. `CompiledComposition` remains the sole canonical compiled authority; no
    second routing graph is introduced.
22. Active configuration preserves every canonical transition deterministically.
23. All four current workflow versions advance to `0.3.0`.
24. Active-config schema version advances to `0.10.0`.
25. Normal generation regenerates canonical state and target output.
26. No workflow runtime, state persistence, invocation history, retry,
    escalation, artifact invalidation, policy engine, or new target is
    introduced.
27. Test-evidence aggregation and AI-evaluation execution semantics remain
    separate roadmap decisions.

# Feature Specification: Agent Decision Experiments

**Feature Branch**: `013-agent-decision-experiments`

**Created**: 2026-05-31

**Status**: Draft

**Input**: Systematic experiments across the five core decisions an Orbit Wars agent makes each turn, to find improvements over agent_v38 by isolating each decision variable.

---

## Background

Each turn an Orbit Wars agent must decide, for each owned planet:

1. **Whether to dispatch** a fleet at all (hold ships vs send)
2. **What to target** (which neutral or enemy planet is most valuable)
3. **How many ships to send** (minimum capture vs larger fleet)
4. **What angle to aim at** (accounting for planet orbit, comet trajectory, sun avoidance)
5. **Which source planet sends** (one planet per target, or multiple planets to one target)

agent_v38 has a fixed answer to each of these:
- Dispatch if surplus above garrison floor
- Target by ROI = production² × time-decay / cost
- Send exactly `target.ships + 1`
- Iterative orbit-lead convergence (well-solved)
- Single best-sender per target (Candidate D)

Decisions 4 and 5-as-implemented are well-established. Decisions 1, 2, 3, and the
alternative to 5 are the live variables. This feature isolates each one and measures
the impact.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Target Scoring Formula (Priority: P1)

As a competitive Kaggle submitter, I want to know whether the current ROI formula
(production² × time-decay / cost) is optimal, or whether a different weighting of
production, distance, and ownership type leads to faster planet accumulation.

**Why this priority**: Target selection is the most upstream decision — it determines
which planets the agent captures and in what order. An incorrect scoring formula
causes systematic misallocation of all fleet resources. All other decisions operate
downstream of this one.

**Independent Test**: Run 50 games per scoring variant vs agent_v38 (seed 0).
Primary metric: win rate. Secondary: average planets controlled at step 100 and
production rate at step 150.

**Acceptance Scenarios**:

1. **Given** two equidistant targets — one with production 5 and one with production 2 —
   **When** the agent selects a target, **Then** each scoring formula consistently
   chooses a target whose selection can be explained by its formula (verifiable from
   game replay).
2. **Given** the current ROI formula as baseline, **When** at least 3 alternative
   scoring formulas are tested over 50 games each, **Then** the best-performing
   formula's win rate relative to baseline can be attributed to earlier high-production
   planet capture (measured at step 100).
3. **Given** a clearly superior scoring formula, **When** adopted as the new default,
   **Then** it achieves ≥55% win rate vs agent_v38 in its standalone test.

---

### User Story 2 - Fleet Sizing Policy (Priority: P2)

As a competitive Kaggle submitter, I want to know the optimal fleet size to dispatch
when capturing a planet — whether sending exactly the minimum needed to capture, sending
more as a buffer, or adapting size to the situation — so that captures succeed at the
highest rate per ship spent.

**Why this priority**: The current policy (`target.ships + 1`) is the cheapest possible
capture but loses to simultaneous enemy sends and does not account for production
accumulation during flight. Fleet sizing directly controls how many ships are spent per
capture, which is the core economy of the game.

**Independent Test**: Run 50 games per fleet-sizing variant vs agent_v38 (seed 0).
Primary metric: win rate. Secondary: capture success rate (fraction of dispatched fleets
that actually change planet ownership) and average ships spent per successful capture.

**Acceptance Scenarios**:

1. **Given** an enemy fleet is simultaneously en route to the same neutral planet,
   **When** the agent uses an adaptive fleet sizing policy, **Then** it sends enough
   ships to win the race without sending so many that it starves other capture attempts.
2. **Given** a target planet that will gain ships during the fleet's travel time,
   **When** the agent calculates fleet size, **Then** the sizing formula accounts for
   production accrual so the fleet arrives with ships ≥ garrison + production × travel_turns.
3. **Given** at least 3 fleet sizing variants (fixed minimum, production-buffered, and
   race-aware) tested over 50 games, **Then** at least one variant outperforms the
   current minimum-capture policy by ≥5 percentage points win rate.

---

### User Story 3 - Garrison Floor Calibration (Priority: P3)

As a competitive Kaggle submitter, I want to know whether the current garrison floor
(3× production or incoming threat, whichever is greater) is correctly calibrated, or
whether a tighter or more adaptive floor unlocks more offensive capacity without
unacceptably increasing planet loss rate.

**Why this priority**: The garrison floor directly controls how many ships are available
for offense. If the floor is too high, surplus never accumulates and the agent can't
capture planets. If too low, owned planets fall to opponents. The right floor is a
critical balance point and has not been swept over a range of values.

**Independent Test**: Run 50 games per garrison floor variant vs agent_v38 (seed 0).
Primary metric: win rate. Secondary: planet-loss count (how many owned planets were
captured by the opponent across 50 games).

**Acceptance Scenarios**:

1. **Given** garrison floor multipliers of at least 1, 2, 3, and 4 tested independently,
   **When** results are compared, **Then** the relationship between floor value and both
   win rate and planet-loss rate is clearly characterised (a sweep, not just one data point).
2. **Given** the best-performing floor multiplier, **When** compared to the current
   floor (3× production + threat), **Then** it either achieves higher win rate with similar
   planet-loss rate, or similar win rate with lower planet-loss rate.
3. **Given** a dynamic garrison floor that scales with game phase (e.g., smaller in early
   game when opponent has fewer ships, larger in late game), **When** evaluated over 50
   games, **Then** it outperforms the static-floor best by ≥3 percentage points win rate.

---

### User Story 4 - Source Assignment Policy (Priority: P4)

As a competitive Kaggle submitter, I want to know whether allowing multiple owned planets
to send to the same target simultaneously — rather than the current single-best-sender
rule — can deliver decisive concentrations of force without disrupting garrison discipline.

**Why this priority**: The single-sender rule (Candidate D) was adopted because earlier
multi-sender approaches broke garrison floors. However, this rule also means the agent
can never overwhelm a well-defended target, limiting its ability to attack the opponent
in the late game. The right multi-sender policy constrains participation by surplus
availability, not by a hard one-per-target rule.

**Independent Test**: Run 50 games per source-assignment variant vs agent_v38 (seed 0).
Primary metric: win rate. Secondary: number of successful enemy-planet captures (as distinct
from neutral captures) per game.

**Acceptance Scenarios**:

1. **Given** two owned planets both have surplus ships above their garrison floor,
   **When** both can reach a high-value target, **Then** a surplus-gated multi-sender
   policy dispatches both fleets in the same turn rather than only one.
2. **Given** a multi-sender policy is active, **When** one of the candidate source
   planets would drop below its garrison floor by participating, **Then** it is excluded
   — garrison discipline is preserved for every participant.
3. **Given** the multi-sender policy tested over 50 games, **When** compared to the
   single-sender baseline, **Then** it achieves ≥50% win rate (does not regress) and
   produces measurably more successful enemy-planet captures per game.

---

### Edge Cases

- What if two scoring formulas produce identical target rankings for most games (symmetric
  maps)? Secondary metrics (step-100 planet count, production rate) become the tiebreaker.
- What if an adaptive fleet size over-sends early, leaving the source planet unable to
  defend itself — does the garrison floor correctly prevent this?
- What if garrison floor = 1× production is so aggressive that the agent loses its home
  planet on turn 10? Record planet-loss rate to detect this pathology.
- What if multi-sender coordination causes two fleets from different owned planets to
  collide en route to the same target (fleet-on-fleet interaction)? Check for fleet
  ordering or deduplication issues.
- What if all four experiments produce small, overlapping confidence intervals — how do
  we determine which improvements are real vs noise at 50-game scale?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The target scoring experiment MUST test at least 3 distinct scoring formulas
  against the current ROI formula as control. Candidates should include: pure production
  priority (ignore distance beyond a threshold), distance-first (linear distance decay
  only), and at least one hybrid.
- **FR-002**: The fleet sizing experiment MUST test at least 3 distinct sizing policies:
  (a) current minimum `target.ships + 1`, (b) production-buffered (`target.ships + 1 +
  target.production × estimated_travel_turns`), and (c) a race-aware policy that scales
  fleet size when an enemy fleet is detected heading for the same target.
- **FR-003**: The garrison floor experiment MUST sweep at least 4 static floor multipliers
  (covering values both smaller and larger than the current 3×) AND test at least one
  dynamic floor variant (floor varies by game phase or production ratio).
- **FR-004**: The source assignment experiment MUST test a surplus-gated multi-sender
  policy where any owned planet with surplus above a configurable threshold may join a
  coordinated dispatch to the highest-priority target, in addition to the current
  single-best-sender baseline.
- **FR-005**: Each experiment MUST be evaluated in isolation — one variable changes vs
  agent_v38 base, all other decisions kept constant — before any combination is attempted.
- **FR-006**: All variants across all experiments MUST be evaluated vs agent_v38 with seed 0
  over ≥50 games. Win rate is the primary selection criterion. Secondary metrics (planet
  count at step 100, production rate at step 150, planet-loss count) MUST be recorded for
  at least the top variant per experiment to support root cause analysis.
- **FR-007**: Once the best variant per experiment is identified, a combined candidate
  (agent_v42) that stacks all four best variants MUST be built and evaluated vs agent_v38
  over ≥50 games.
- **FR-008**: All variant results MUST be recorded in `experiments/013-agent-decisions.md`
  with a results table before any agent is promoted.
- **FR-009**: All agents MUST comply with Kaggle actTimeout (≤1 second per turn) using
  pure Python + stdlib/numpy — no ML inference at runtime.

### Key Entities

- **Scoring Formula**: A function that takes a candidate planet and source planet as inputs
  and returns a scalar priority score. Controls which target each source planet prefers.
- **Fleet Sizing Policy**: A function that takes source planet, target planet, and
  observable context (enemy fleets, transit time) and returns the number of ships to send.
- **Garrison Floor**: The minimum ships an owned planet must retain. Can be a fixed
  multiplier on production, a function of incoming threats, or dynamic by game phase.
- **Source Assignment Policy**: The rule that determines which owned planets may dispatch
  to a given target in the same turn (single-best-sender vs surplus-gated multi-sender).
- **Experiment Variant**: A single-variable modification of agent_v38, named by experiment
  and variant number (e.g., `013-scoring-1`, `013-fleet-size-2`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one scoring formula variant achieves ≥55% win rate vs agent_v38
  over 50 games (seed 0), confirming the current ROI formula is improvable.
- **SC-002**: At least one fleet sizing variant achieves ≥55% win rate vs agent_v38
  over 50 games (seed 0), confirming minimum-capture sizing is improvable.
- **SC-003**: The garrison floor sweep clearly identifies the optimal static multiplier
  (characterised by a win-rate curve across at least 4 values), and the best static
  variant achieves ≥50% win rate.
- **SC-004**: The surplus-gated multi-sender variant achieves ≥50% win rate vs agent_v38
  (no regression) and produces ≥20% more enemy-planet captures per game than single-sender.
- **SC-005**: The combined agent (agent_v42) achieves ≥60% win rate vs agent_v38 over 50
  games with seed 0.
- **SC-006**: All experiment results are documented in `experiments/013-agent-decisions.md`
  before any promotion decision.
- **SC-007**: All agent variants maintain turn time under 1 second (pure Python/numpy).

## Assumptions

- agent_v38 is the correct control baseline for all experiments. agent_v40 is a reference
  point but not the comparison target.
- Decision 4 (orbit-lead/navigation) is not being re-examined — the iterative convergence
  in agent_v38 is considered solved.
- The 4-fold map symmetry means symmetric self-play vs agent_v38 (same agent on both sides)
  is an appropriate test. A win rate significantly above 50% against an identical opponent
  indicates a genuine asymmetry in strategy, which is the goal.
- Testing each of the four decisions in isolation (one variable at a time) is a valid
  experimental design given the 50-game eval scale. Interactions between decisions may
  exist but will be detected when the combined agent is evaluated.
- Kaggle submission is explicitly out of scope. The feature ends at local evaluation.
  Promotion to current best agent is a separate decision after eval results are reviewed.
- agent_v42 will be implemented as a self-contained Python file at the repo root,
  following the naming convention of all prior agents.
- The eval harness (`eval.py --agent0 --agent1 --games 50 --seed 0`) is the
  authoritative benchmark throughout this feature.

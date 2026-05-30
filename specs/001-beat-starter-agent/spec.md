# Feature Specification: Beat the Getting Started Agent

**Feature Branch**: `001-beat-starter-agent`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Do first experiment in making a new agent that can beat the getting started agent."

## Clarifications

### Session 2026-05-29

- Q: What strategic improvement should the new agent implement over the nearest-planet-sniper? → A: Production-weighted targeting — score targets by production/distance ratio (best value per travel cost)
- Q: Should the evaluation script save results to disk or print only? → A: Print only — results go to stdout, nothing written to disk

## User Scenarios & Testing *(mandatory)*

### User Story 1 - New Agent Beats Baseline (Priority: P1)

A developer creates a new Orbit Wars agent that consistently wins against the built-in "getting started" nearest-planet-sniper agent in head-to-head matches.

**Why this priority**: This is the core goal of the experiment — establishing that a smarter strategy exists and works in practice.

**Independent Test**: Can be fully tested by running `kaggle_environments` locally, pitting the new agent against `main.py` (the getting-started agent) over multiple seeded games, and verifying the new agent wins more than 50% of matches.

**Acceptance Scenarios**:

1. **Given** a fresh game with the new agent as Player 0 and the getting-started agent as Player 1, **When** the game runs for up to 500 turns, **Then** the new agent's final ship count exceeds the getting-started agent's final ship count.
2. **Given** 10 games with different random seeds, **When** all games complete, **Then** the new agent wins at least 7 out of 10 (70% win rate).
3. **Given** the new agent is placed in any starting quadrant, **When** the game runs, **Then** the agent performs consistently regardless of starting position.

---

### User Story 2 - Observable Strategy Difference (Priority: P2)

A developer reviewing the game replay can identify a concrete strategic behavior in the new agent that the getting-started agent lacks.

**Why this priority**: The experiment should yield a learnable insight, not just a lucky win — it should be clear *why* the new agent is better.

**Independent Test**: Can be tested by running a single game, rendering it, and being able to point to at least one decision type (e.g., fleet allocation, target selection, timing) that differs from the nearest-sniper logic.

**Acceptance Scenarios**:

1. **Given** a completed game replay, **When** the developer reviews turn-by-turn actions, **Then** the new agent can be observed bypassing a nearer planet to target a farther planet with a higher production/distance score — a behavior the getting-started agent never exhibits.
2. **Given** the new agent code, **When** a developer reads it, **Then** the strategic reasoning is clear from the structure or comments.

---

### User Story 3 - Local Test Harness (Priority: P3)

A developer can run a local head-to-head evaluation with a single command and get a clear win/loss result.

**Why this priority**: Rapid iteration requires a fast feedback loop — re-running experiments must be frictionless.

**Independent Test**: Can be tested by running a single command that plays N games and prints results without requiring a Kaggle submission.

**Acceptance Scenarios**:

1. **Given** the project is checked out locally, **When** the developer runs the evaluation command, **Then** it prints per-game results (winner, final scores) and an aggregate win rate within 30 seconds.
2. **Given** an agent file path, **When** the command is run, **Then** no manual code edits are needed to swap which agent is being tested.

---

### Edge Cases

- What happens when the new agent and the getting-started agent end with identical ship counts? (Treat as a draw, not a win.)
- How does the agent behave when all planets are owned (no neutral targets left)?
- How does the agent handle the sun obstacle when angles would route a fleet through it?
- What happens if the agent has no ships to send on a given turn?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The new agent MUST be implemented as a single `agent(obs)` function in a Python file compatible with the `kaggle_environments` Orbit Wars environment.
- **FR-002**: The new agent MUST achieve a win rate of at least 70% against the getting-started nearest-planet-sniper agent across 10 games with varied seeds.
- **FR-003**: The new agent MUST implement production-weighted targeting — scoring candidate planets by production/distance ratio and attacking the highest-value target rather than the nearest one.
- **FR-004**: The new agent MUST return a valid action list each turn — never crashing or returning an invalid format.
- **FR-005**: The new agent MUST complete each turn within the 1-second time budget.
- **FR-006**: A local evaluation script MUST allow head-to-head testing between two agent files without requiring a Kaggle submission.
- **FR-007**: The evaluation script MUST print per-game winner, final scores for both agents, and overall win rate to stdout. No results file is written to disk.

### Key Entities

- **Agent**: A Python function `agent(obs) -> list` that encodes the decision-making strategy; has a file path and strategy name.
- **Game**: A single Orbit Wars episode with a fixed seed; has a winner, final scores per player, and a turn count.
- **Evaluation Run**: A batch of N games between two agents; has an aggregate win rate and per-game results.
- **Strategy**: The decision logic the agent uses; specifically production-weighted targeting, where each candidate planet is scored by its production divided by travel distance, and the highest-scoring target is selected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The new agent wins at least 7 out of 10 head-to-head games against the getting-started agent across varied seeds.
- **SC-002**: The new agent completes each turn's decision within the allotted time budget across all test games (zero timeouts).
- **SC-003**: A developer can run the full local evaluation (10 games) and see results in under 60 seconds.
- **SC-004**: In at least one game replay, the new agent demonstrably bypasses a nearby low-production planet to attack a farther high-production one — a behavior the nearest-sniper never exhibits.

## Assumptions

- The "getting started" agent is the nearest-planet-sniper in `main.py` — this is the baseline to beat.
- Local testing uses `kaggle_environments` (≥1.28.0) with the default game configuration (500 turns, no custom parameters).
- A 2-player game format is used for head-to-head evaluation; 4-player games are out of scope for this experiment.
- The new agent does not use external models, pre-computed tables, or network calls — it is a pure Python rule-based strategy.
- Mobile/web visualization is out of scope; notebook rendering via `env.render()` is sufficient for replay review.
- The experiment is exploratory — a single improved strategy is sufficient; exhaustive optimization is out of scope for v1.

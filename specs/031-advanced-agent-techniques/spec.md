# Feature Specification: Advanced Agent Techniques (Round 8)

**Feature Branch**: `031-advanced-agent-techniques`

**Created**: 2026-06-13

**Status**: Draft

**Input**: User description: "Make agent better, by employing more advanced techniques and strategies."

## Overview

The competition agent has matured through a long heuristic lineage culminating in the current best, `agent_v68`. Recent rounds (5, 6, 7) show diminishing returns: most candidate tweaks now wash out near 50%, and the agent still **loses every game (0%)** against the strongest known benchmark opponent, `slawekbiel_agent`. This round changes the improvement strategy: instead of small parameter tweaks to the existing greedy-plus-beam pipeline, it evaluates **qualitatively more advanced decision-making techniques** — deeper/wider lookahead, stronger search algorithms, richer position evaluation, better opponent modeling, and multi-planet coordinated strategy — with the explicit goal of (a) beating the frozen current best in self-play and (b) for the first time, winning a non-trivial share of games against the benchmark opponent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Break the benchmark wall (Priority: P1)

As the competition entrant, I want the agent to employ a more advanced decision technique that wins a measurable share of games against `slawekbiel_agent`, so that the lineage stops being hard-capped at 0% against the strongest known opponent and has a path to a higher Kaggle ranking.

**Why this priority**: The 0% benchmark result is the single clearest signal that the current technique class has plateaued. Any technique that moves this number off zero is the most valuable possible outcome of the round; everything else is secondary.

**Independent Test**: Fork the current best agent, implement one advanced technique behind a toggle, and run ≥30 side-alternating games against `slawekbiel_agent`. The story succeeds if the new technique wins strictly more than 0% (with the round's confidence threshold) while not regressing self-play strength below the current best.

**Acceptance Scenarios**:

1. **Given** the frozen current best agent at 0% vs the benchmark, **When** an advanced-technique candidate is evaluated over ≥30 side-alternating games vs the benchmark, **Then** its win rate, the side-by-side comparison to the current best's 0%, and the per-game outcomes are recorded in an experiment log.
2. **Given** a candidate that wins games against the benchmark, **When** it is also evaluated in self-play against the frozen current best, **Then** it must not regress (self-play win rate ≥ the round's pass threshold) for it to be adopted.
3. **Given** a candidate that improves vs the benchmark but regresses in self-play, **When** results are reviewed, **Then** the regression is documented and the candidate is rejected or revised rather than silently adopted.

---

### User Story 2 - Adopt a stronger search/decision technique that beats the current best (Priority: P1)

As the competition entrant, I want at least one genuinely more advanced technique (e.g., deeper or wider lookahead, a stronger search algorithm than the current beam, a richer evaluation function, or improved opponent modeling) that beats the frozen current best in self-play, so that the new round produces a new current best rather than another wash.

**Why this priority**: The round's headline deliverable is a new best agent. Advancing the *technique class* (not just constants) is what distinguishes this round from the prior incremental rounds that plateaued.

**Independent Test**: Implement each advanced-technique candidate behind an independent toggle on a fork of the current best, evaluate each over ≥50 side-alternating self-play games vs the frozen current best, and confirm at least one passes the round's win-rate threshold without exceeding the per-turn time budget.

**Acceptance Scenarios**:

1. **Given** the frozen current best as the self-play baseline, **When** each advanced-technique candidate is evaluated over ≥50 side-alternating games, **Then** each candidate's win rate and per-turn timing are recorded.
2. **Given** multiple passing candidates, **When** they are combined into a single configuration, **Then** the combination is re-evaluated over ≥50 side-alternating games vs the frozen current best and the combined result is recorded.
3. **Given** the best resulting configuration, **When** it is re-verified over ≥30 side-alternating games against the benchmark opponent, **Then** the result confirms the self-play gain does not come at the cost of a benchmark regression.
4. **Given** a candidate whose decision logic occasionally exceeds the per-turn time budget, **When** timing is measured, **Then** the candidate is rejected or bounded until it fits the budget, because exceeding the budget forfeits turns.

---

### User Story 3 - Preserve safety and legality guarantees (Priority: P2)

As the competition entrant, I want every advanced-technique candidate to retain the lineage's hard safety guarantees — no fleet lost to the sun, no fleet sent out of bounds, every turn returned within the time limit, and no engine exploits — so that a more sophisticated technique never reintroduces a class of loss the lineage already eliminated.

**Why this priority**: Advanced search and evaluation changes are exactly where regressions in path safety and timing creep back in. Catching them is necessary for any candidate to be adoptable, but it gates rather than creates value, so it sits below the two P1 stories.

**Independent Test**: Across the diagnostic games for every candidate, confirm zero sun losses, zero out-of-bounds losses, and zero per-turn time-limit breaches; any breach disqualifies the candidate regardless of win rate.

**Acceptance Scenarios**:

1. **Given** any candidate's diagnostic games, **When** game outcomes are inspected, **Then** sun losses and out-of-bounds losses are both zero.
2. **Given** any candidate, **When** per-turn decision time is measured across a full game, **Then** every turn completes within the time budget with margin.

---

### Edge Cases

- What happens when an advanced search technique cannot complete within the per-turn time budget on a worst-case board (maximum planets and in-transit fleets)? It MUST degrade gracefully to a valid, safe move rather than time out.
- How does the agent behave when the more advanced opponent model mispredicts the opponent? A worse opponent model must not make decisions worse than the current best's existing model.
- What happens when a deeper/wider search surfaces a move the current evaluation scores highly but that loses safety guarantees (sun/OOB)? Safety filters MUST still reject it.
- What happens if every advanced-technique candidate fails to beat the current best? The round still produces a documented outcome and the current best is retained unchanged (mirroring prior wash rounds).
- How is non-determinism handled so results are reproducible enough to compare candidates fairly?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The round MUST fork the current best agent into a new agent file as a frozen baseline; the current best file MUST NOT be modified.
- **FR-002**: The round MUST evaluate at least two candidate techniques that are *qualitatively more advanced* than parameter tweaks to the existing pipeline — drawn from: deeper or wider lookahead search, a stronger search algorithm than the current beam (e.g., MCTS or full game-tree search with pruning), a richer position-evaluation function, improved opponent modeling, or multi-planet coordinated strategy.
- **FR-003**: Each candidate technique MUST be implemented behind an independent on/off toggle so it can be isolated, and the committed default state MUST leave the new agent functionally equivalent to the frozen current best if nothing passes.
- **FR-004**: Each candidate MUST be evaluated in self-play over at least 50 side-alternating games against the frozen current best, and the win rate recorded.
- **FR-005**: Each candidate MUST be evaluated over at least 30 side-alternating games against the benchmark opponent (`slawekbiel_agent`), and its win rate recorded alongside the current best's known 0% for direct comparison.
- **FR-006**: A candidate MUST be considered passing only if it meets the round's self-play win-rate threshold AND does not regress against the benchmark opponent relative to the current best.
- **FR-007**: All passing candidates MUST be combined into a single configuration and the combination re-evaluated over at least 50 side-alternating self-play games and at least 30 games against the benchmark.
- **FR-008**: Every candidate and the final combination MUST preserve the lineage's safety guarantees: zero sun losses, zero out-of-bounds losses, and zero per-turn time-budget breaches across their diagnostic games.
- **FR-009**: The agent MUST remain a self-contained submission package using only the runtime libraries already permitted for the lineage (standard library plus the competition environment); no new third-party runtime dependency may be introduced into the submitted agent.
- **FR-010**: If a candidate's technique can exceed the per-turn time budget, it MUST include a bound or graceful-degradation fallback that guarantees a valid move within budget.
- **FR-011**: Each phase (technique selection, per-candidate evaluation, combination, and benchmark re-verification) MUST be documented in an experiment log before any external submission.
- **FR-012**: The new best configuration MUST be adopted as current best only if it beats the frozen current best at the round's confidence threshold; otherwise the current best is retained and the negative result documented.
- **FR-013**: On adoption of a new best, the project's agent index (README table) and the build's default agent pointer MUST be updated to reflect the new current best.
- **FR-014**: The round MUST respect documented prior failure traps from earlier rounds so it does not re-test techniques already shown to wash out or regress, unless implemented in a materially different way that addresses the prior failure cause.

### Key Entities

- **Frozen Baseline Agent**: The current best agent at round start (`agent_v68`), copied to a new file and never modified during the round; serves as both fork point and self-play opponent.
- **Candidate Technique**: One qualitatively-advanced decision technique, gated behind an independent toggle, with an isolated code region so toggles compose for the combination run.
- **Benchmark Opponent**: The strongest known loadable opponent (`slawekbiel_agent`), against which the current best currently wins 0%; the primary external yardstick for this round.
- **Evaluation Result**: Per-candidate record of self-play win rate, benchmark win rate, per-turn timing, and safety-violation counts.
- **Experiment Log**: The documented record of each phase, including negative results, used to justify adoption or rejection.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one advanced-technique candidate wins strictly more than 0% of games against the benchmark opponent over the ≥30-game evaluation — the first non-zero benchmark result in the lineage.
- **SC-002**: The round produces a new current best whose self-play win rate against the frozen prior best is at or above the round's pass threshold (≥52% over ≥50 side-alternating games), OR documents that no candidate passed and the prior best is retained.
- **SC-003**: The adopted configuration shows no benchmark regression: its win rate vs the benchmark is greater than or equal to the prior best's (0%) over ≥30 games.
- **SC-004**: Across all diagnostic games for every evaluated candidate and the final combination, sun losses, out-of-bounds losses, and per-turn time-budget breaches each total zero.
- **SC-005**: Every per-turn decision completes within the competition time budget with margin on worst-case boards (no forfeited turns).
- **SC-006**: At least two qualitatively-advanced techniques (not mere constant tweaks) are implemented and evaluated, each documented with its win rates and the decision to adopt or reject.

## Assumptions

- "More advanced techniques and strategies" means advancing the *decision-making technique class* (search algorithm, lookahead depth/width, evaluation richness, opponent modeling, multi-planet coordination), not retuning existing constants; this is treated as the next experiment round (Round 8) in the established lineage.
- The current best at round start is `agent_v68`, and the benchmark opponent is `slawekbiel_agent` (current best wins 0% against it), per the latest recorded results.
- The round's pass threshold for self-play adoption is ≥52% over ≥50 side-alternating games, consistent with prior rounds; the benchmark non-regression bar is "≥ the current best's 0%."
- The agent remains a single, self-contained submission file using only the standard library plus the competition environment at play time; any heavier tooling (e.g., for offline analysis or model training) is local-only and out of the submitted package.
- The per-turn time budget and safety constraints (sun-path avoidance, in-bounds dispatch) carry over unchanged from the current lineage.
- Kaggle submission, if any, remains manual and happens only after local evaluation confirms an improvement, per the project constitution.
- Evaluation uses the existing self-play and opponent-sweep harness with side-alternation to remove positional bias.

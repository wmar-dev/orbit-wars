# Feature Specification: Experiments Round 4

**Feature Branch**: `024-experiments-round-4`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "Try another round of experiments"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Improved Opponent Model for Beam Search (Priority: P1)

The current opponent model (`_sim_opponent_step_v2`) dispatches surplus ships from each enemy planet to the nearest non-ally target using only position-based targeting. This is weaker than even our baseline agent and likely far weaker than slawekbiel. Since beam search simulates this unrealistic opponent, all evaluations past turn 1 compound errors — which explains why deeper search (depth=15/20) degraded performance in round 3. A more realistic opponent model should make beam search evaluations more accurate, improving tactical decisions against strong opponents.

**Why this priority**: The 0% win rate vs slawekbiel is the single biggest gap. Round 3 showed deeper search with the wrong opponent model makes worse decisions — fixing the model is prerequisite to any search improvement. Timing budget has >50x headroom (p99 < 15ms of 800ms).

**Independent Test**: Create `agent_v64.py` from v63. Implement opponent model v3 using production-weighted targeting (closest v62 behavioral match). Run 50-game eval vs v62 baseline. Target: ≥52% win rate. Then run opponent sweep including slawekbiel — measure win rate improvement from 0%.

**Acceptance Scenarios**:

1. **Given** opponent model v3 is enabled, **When** running a 50-game self-play eval vs v62, **Then** win rate ≥52% (no regression from v63's 52%).
2. **Given** opponent model v3 is enabled, **When** running an opponent sweep vs slawekbiel (20 games), **Then** win rate >0% (gap begins to close).
3. **Given** opponent model v3 is logged with per-turn timing, **When** running benchmark games, **Then** p99 timing stays under 800ms.

---

### User Story 2 — Multi-Turn Plan Generation (Priority: P2)

The current beam search only evaluates alternative single-turn dispatches — it replaces one planet's dispatch with a different target and simulates for SEARCH_DEPTH steps. It never generates multi-turn plans (e.g., "skip this turn to save ships, then send a bigger fleet next turn"). This limits the search to tactical substitutions rather than strategic planning. A flat plan generator that considers "wait-and-build" candidates (zero dispatches followed by larger dispatches) or sequential-wave attacks could find qualitatively different strategies that the current search misses.

**Why this priority**: The slawekbiel agent likely sequences multi-turn attacks (feint with small fleet, follow with large fleet). Our agent never considers two-turn plans — each turn is a fresh greedy dispatch + beam overlay. Adding multi-turn candidates may unlock qualitatively different strategies.

**Independent Test**: In `agent_v64.py`, add a multi-turn candidate generator that creates dummy "skip" moves for one turn, allowing the beam search to evaluate plans where the agent deliberately waits. Run 50-game eval vs v62. Target: ≥52% win rate. Check if slawekbiel win rate improves.

**Acceptance Scenarios**:

1. **Given** multi-turn planning is enabled, **When** the beam search evaluates candidates, **Then** at least one candidate includes a "skip" (zero dispatches) in the first turn followed by larger dispatches in subsequent simulated turns.
2. **Given** multi-turn planning is enabled, **When** running a 50-game eval vs v62, **Then** win rate ≥52%.
3. **Given** multi-turn plans are generated, **When** the agent has insufficient ships to capture any target, **Then** it waits rather than sending wasteful small fleets.

---

### User Story 3 — Phase-Detection Dispatch (Priority: P3)

The agent currently uses the same dispatch thresholds and heuristics throughout the entire game. Early game (expansion) and late game (elimination) have different optimal behaviors: early game favors rapid neutral capture even at low ROI, while late game favors coordinated attacks on opponent home planets. A phase-detection system that adjusts garrison floor, splinter window, and target selection based on remaining planets and opponents alive could improve late-game conversion.

**Why this priority**: Of the three experiments this is the lowest risk — it only adjusts scalar parameters that are already tunable. It may not close the slawekbiel gap alone but could improve win rate against opponents with strong early-game defense.

**Independent Test**: In `agent_v64.py`, adjust GARRISON_FLOOR_FACTOR and SPLINTER_WINDOW based on number of surviving opponents and remaining planets. Run 50-game eval vs v62. Target: ≥52% win rate.

**Acceptance Scenarios**:

1. **Given** phase detection is enabled, **When** >80% of neutrals are captured, **Then** the garrison floor decreases and more ships are sent to attack opponent planets.
2. **Given** phase detection is enabled, **When** only 2 players remain, **Then** the agent prioritizes multi-source attacks on the remaining opponent.
3. **Given** phase detection is enabled, **When** running a 50-game eval vs v62, **Then** win rate ≥52%.

---

### Edge Cases

- What happens when opponent model v3 is used but the real opponent plays totally differently (e.g., slawekbiel uses beam search vs our beam search)? The simulation will never match reality perfectly, but using a stronger simulated opponent should reduce the mismatch compared to the current nearest-target baseline.
- What happens when multi-turn planning is evaluated against a simple opponent that attacks every turn? The "wait" behavior could let the opponent capture free territory. The beam search should automatically reject skip plans that lead to worse outcomes.
- What happens when phase detection fires too early (e.g., most planets are still neutral but the agent switches to elimination mode)? The phase must be conservative — only transition to elimination when ≥80% of planets are owned by some player.
- What happens when opponent model v3 adds timing overhead? The current opponent is extremely fast (nearest target, no path checking). v3 will use more compute but timing tests (SC-002) will verify budget compliance before considering combined configuration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The opponent model v3 MUST use production-weighted or ROI-based target selection (matching v62-level behavior), replacing the current nearest-target surplus-only model.
- **FR-002**: The opponent model v3 MUST be independently togglable via a constant (`OPPONENT_MODEL_V3_ENABLED`).
- **FR-003**: The multi-turn plan generator MUST create at least one "skip" candidate per game turn where the beam search can evaluate waiting vs dispatching.
- **FR-004**: Multi-turn planning MUST be independently togglable via a constant (`MULTI_TURN_PLAN_ENABLED`).
- **FR-005**: Phase detection MUST adjust at least two of: garrison floor factor, splinter window, target selection criteria based on game state.
- **FR-006**: Phase detection MUST be independently togglable via a constant (`PHASE_DETECTION_ENABLED`).
- **FR-007**: `agent_v64.py` MUST be created as a copy of `agent_v63.py`, serving as the experimental platform. `agent_v63.py` remains frozen as the baseline.
- **FR-008**: All experiments MUST be evaluated against v63 (with v62 as a secondary reference) using 50-game evals with --swap. Each eval records win rate, draw rate, and per-turn timing (p50/p95/p99).

### Key Entities

- **Opponent model v3**: Replacement for `_sim_opponent_step_v2` that uses production-weighted or ROI-based target selection rather than nearest-target surplus dispatch. Intended to more closely match real opponent behavior in forward simulation.
- **Multi-turn plan generator**: Extension to `_gen_beam_candidates` that produces candidates where some planets send zero ships on the first turn (building up for a larger subsequent send), allowing the beam search to evaluate non-greedy strategies.
- **Phase detection**: Game-state analysis that determines early/mid/late game based on remaining neutral planets, surviving opponents, and turn count. Adjusts dispatch parameters accordingly.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one of the three experiments achieves ≥52% win rate vs v62 in a 50-game self-play eval with --swap.
- **SC-002**: All experiments complete with p99 per-turn timing < 100ms (12.5% of 800ms budget), confirming enormous headroom and no risk of Kaggle timeout.
- **SC-003**: The slawekbiel opponent sweep shows improvement from 0% to >0% win rate for at least one experiment.
- **SC-004**: At least one experiment passes and is included in the combined configuration. The combined config improves over v63's 52% vs v62 baseline.
- **SC-005**: All experiment results are logged in `experiments/2026-06-06-experiments-round4.md` with win rates, sample counts, and conclusions.

## Assumptions

- `agent_v64.py` is created as a copy of v63 serving as the experimental platform. v63 remains frozen as the baseline for all comparisons.
- All experiments are evaluated against v63 (current best, 52% vs v62) as the primary baseline. v62 is the secondary reference for regression testing.
- The slawekbiel opponent's advantage comes from a stronger evaluation function or opponent model in its search, not from hardware advantages or different fundamental architecture.
- The 50-game eval with --swap (25 games per side) provides sufficient statistical power for a ≥52% win rate threshold (equivalent to ~56% win rate on a single side).
- The opponent model v3 does not need to perfectly match slawekbiel — matching v62-level behavior is sufficient to demonstrate the concept improves over nearest-target.
- Multi-turn planning effectiveness depends on the beam search depth being sufficient to realize the benefit of waiting; SEARCH_DEPTH=10 should be adequate.

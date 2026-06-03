# Feature Specification: Early Expansion Experiments from Replay 78539022

**Feature Branch**: `018-replay-neutral-fleet-experiments`

**Created**: 2026-06-02

**Status**: Draft

**Input**: User description: "It looks like from replay/78539022.json, I lost in the begining since I went after a neutral planet with a larger first while the opponent went for a neutral planet with a smaller fleet. What experiments can I develop from this replay?"

## Background & Replay Analysis

Replay 78539022 ended in a loss (reward: -1 for wmar/P0, +1 for HY2017/P1). The critical divergence happened in the first 20 steps:

| | wmar (P0) | HY2017 (P1) |
|---|---|---|
| Home planet | Planet 4 (52 ships, growth=1.69) | Planet 7 (52 ships, growth=1.69) |
| First action step | Step 12 | Step 6 |
| First neutral target | Planet 16 (30 ships, growth=2.61) | Planet 11 (18 ships, growth=2.09) |
| Fleet sent | 31 ships | 19 ships |
| Growth efficiency (growth/cost) | 0.087 | 0.116 |
| Planets owned by step 20 | 2 | 3 |
| Planets owned by step 30 | 3 | 6 |

P0 targeted the planet with the highest absolute growth rate but highest capture cost. P1 targeted the cheaper planet, which had a better growth-per-ship-invested ratio. P1 also acted 6 steps earlier, compounding the lead. By step 30, P0 was losing 3 vs 6 planets — a snowball that never recovered.

Symmetrically, P0's optimal mirror of P1's first target would have been Planet 8 (18 ships, growth=2.09) — the same tier planet on P0's side. Instead P0 targeted Planet 16 (30 ships), which cost ~70% more ships to capture.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Growth-Efficiency First Target (Priority: P1)

The developer runs a new agent variant that selects the first neutral planet based on growth_rate / capture_cost ratio rather than absolute growth rate, and evaluates whether this produces better early-game expansion than the current agent.

**Why this priority**: This directly addresses the root cause identified in the replay — choosing a more expensive planet with marginally higher growth over a cheaper planet with better ROI. Higher priority because it targets the most critical decision point.

**Independent Test**: Pit the new variant against the current best agent across 50+ games with seeds that include early-expansion scenarios. Check if the new agent captures a first neutral at an equal or lower ship cost.

**Acceptance Scenarios**:

1. **Given** a game start, **When** the agent selects its first neutral target, **Then** it chooses the planet with the highest (growth_rate / estimated_capture_cost) ratio among reachable neutrals.
2. **Given** two neutral planets at equal distance — one with 18 ships/growth 2.09 and one with 30 ships/growth 2.61 — **When** the agent decides, **Then** it picks the 18-ship planet (efficiency 0.116 > 0.087).
3. **Given** the new variant plays 50 games, **When** compared to the baseline, **Then** win rate improves by at least 3 percentage points.

---

### User Story 2 - Earlier First Fleet Dispatch (Priority: P2)

The developer tests whether dispatching the first fleet sooner (sending as soon as the agent accumulates enough ships to capture the cheapest nearby neutral) improves win rate.

**Why this priority**: P1 acted at step 6 vs P0's step 12 — a 6-step head start that translated into capturing a second planet before P0 captured its first. Earlier action means earlier compounding growth.

**Independent Test**: Count the step at which the first fleet is dispatched across 50 games. The new variant should dispatch ≥5 steps earlier on average than the baseline.

**Acceptance Scenarios**:

1. **Given** a game start with a nearby cheap neutral (≤20 ships), **When** the agent accumulates enough ships to capture it, **Then** it dispatches a fleet within 2 steps of having sufficient ships.
2. **Given** the earlier-dispatch variant plays 50 games, **When** compared to the baseline, **Then** it captures its first neutral ≥5 steps earlier on average.
3. **Given** early dispatch depletes home planet below a safety threshold, **When** the opponent's nearest fleet is farther than 10 steps, **Then** the agent still dispatches rather than hoarding.

---

### User Story 3 - Minimum-Viable Fleet Sizing (Priority: P2)

The developer tests an agent that sends just enough ships to capture a neutral (accounting for planet growth during transit) rather than a fixed large fleet, freeing up ships for parallel expansion.

**Why this priority**: P0 sent 31 ships to a 30-ship planet — essentially 1 ship above minimum. But the fixed-fleet approach wastes ships when the planet grows during flight. Better sizing enables simultaneous multi-target expansion.

**Independent Test**: Measure average ships-per-capture across 50 games. New variant should reduce ships-per-first-capture by ≥15% compared to baseline.

**Acceptance Scenarios**:

1. **Given** a neutral planet with 18 ships and growth rate 2.09 at 8 steps of travel, **When** computing fleet size, **Then** the agent sends at least 18 + ceil(2.09 × 8) + safety_buffer ships.
2. **Given** a neutral planet with 30 ships, **When** sending a capture fleet, **Then** the agent does not send more than 20% above the minimum required.
3. **Given** minimum-viable sizing frees extra ships, **When** a second cheap neutral is available, **Then** the agent targets it simultaneously rather than waiting.

---

### User Story 4 - Multi-Target Parallel Rush (Priority: P3)

The developer tests targeting two neutrals in rapid succession in the early game — the cheap near one first, then immediately the next cheapest — mirroring P1's strategy of capturing planets 11 and 21 within 8 steps of each other.

**Why this priority**: P1 sent a second fleet at step 14 (8 steps after first dispatch) to Planet 21. By step 20, P1 had 3 planets growing while P0 had 2. The multi-target rush compounds growth faster.

**Independent Test**: Count planets owned by step 25 across 50 games. New variant should average ≥2.5 planets by step 25 vs baseline's expected ≤2.

**Acceptance Scenarios**:

1. **Given** the first fleet has been dispatched, **When** the home planet has regenerated enough ships, **Then** a second fleet targets the next-best efficiency neutral within 10 steps.
2. **Given** two targets are sent in parallel, **When** both fleets are in transit, **Then** neither intercept each other or drain the home planet below a defense threshold.
3. **Given** the rush variant plays 50 games, **When** planet count at step 25 is measured, **Then** average planet count meets or exceeds 2.5.

---

### Edge Cases

- What happens when both players target the same neutral simultaneously — should the agent detect incoming enemy fleets and redirect?
- How does the efficiency-scoring heuristic behave when all nearby neutrals have similar cost (no clear winner)?
- What if the cheapest neutral is in a bad strategic position (closer to opponent)?
- When planet positions orbit over time, does the "nearest cheap neutral" change between computation and fleet arrival?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST compute a growth-efficiency score (growth_rate / estimated_capture_cost) for each neutral planet during target selection.
- **FR-002**: Estimated capture cost MUST account for neutral planet growth during fleet transit time (distance / ship_speed).
- **FR-003**: The agent MUST dispatch its first fleet no later than the step when home planet ships exceed the minimum capture cost of the cheapest reachable neutral.
- **FR-004**: Fleet sizes MUST be computed dynamically as min_capture_ships + safety_buffer rather than a fixed constant.
- **FR-005**: After dispatching the first fleet, the agent MUST evaluate a second target immediately and dispatch when home planet ships are sufficient.
- **FR-006**: Each experiment variant MUST be implemented as a standalone agent file that can be evaluated with `make eval` or equivalent.
- **FR-007**: Experiment results MUST be recorded with win rates against the current best agent (agent_v57) across at least 50 games per variant.

### Key Entities

- **Experiment Variant**: A versioned agent file implementing one or more of the experimental heuristics, benchmarked against a baseline.
- **Growth Efficiency Score**: A per-planet metric = growth_rate / (current_ships + growth_rate × travel_steps); higher is better.
- **Minimum Capture Cost**: The number of ships needed to flip a neutral, accounting for its growth during fleet travel time.
- **Safety Buffer**: Extra ships added to the fleet to tolerate planet growth estimation errors; tunable parameter.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one experiment variant achieves a win rate ≥5 percentage points above agent_v57 when evaluated on ≥50 games.
- **SC-002**: Variants that use growth-efficiency scoring capture their first neutral at lower average cost (ships sent per game) than agent_v57.
- **SC-003**: The multi-target parallel rush variant owns ≥2.5 planets on average by game step 25 (vs ≤2 for agent_v57).
- **SC-004**: The earlier-dispatch variant sends its first fleet ≥5 steps earlier on average than agent_v57.
- **SC-005**: All variants complete evaluation in under 10 minutes per 50-game run.

## Assumptions

- Replay 78539022 is representative of a class of early-game scenarios; the identified failure mode (expensive first neutral) is not seed-specific.
- The current best agent is agent_v57 and serves as the baseline for all comparisons.
- Game symmetry holds: planets near P0's home are structurally equivalent to those near P1's home, enabling direct comparison of target choices.
- Planet growth during transit is predictable (linear, known growth rate) so minimum-capture-cost calculations are tractable.
- Existing eval infrastructure (Makefile, agent file conventions) is used to run experiments; no new tooling is needed.
- Mobile/UI concerns are out of scope; this is a pure agent logic experiment feature.

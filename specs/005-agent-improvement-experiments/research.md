# Research: Agent Improvement Experiments

**Branch**: `005-agent-improvement-experiments` | **Date**: 2026-05-30

All clarification questions were resolved in the spec session. This document consolidates the design decisions and supporting rationale.

---

## Decision Log

### D-001: Candidate numbering

**Decision**: agent_v11–v14 for isolated candidates (A–D), agent_v15 for the combined agent.

**Rationale**: Continues the existing sequential versioning convention. One file per mechanic makes experiment isolation and rollback unambiguous.

**Alternatives considered**: Branching from v10 with lettered suffixes (v10a, v10b) — rejected because it breaks the linear version history and confuses README tracking.

---

### D-002: Redundant fleet detection (Candidate A)

**Decision**: A fleet is redundant if `sum(f.ships for f in friendly_fleets_en_route_to_target) >= target.ships + 1`.

**Rationale**: Summing all en route fleets gives the most accurate picture of committed firepower. A single-fleet check would miss coordinated multi-fleet coverage.

**Alternatives considered**: Track only the nearest fleet — simpler but misses multi-fleet coordination cases.

---

### D-003: Garrison floor sub-experiments (Candidate B)

**Decision**: Evaluate `production × 5`, `production × 10`, and fixed `10` as separate sub-experiments under agent_v12. The best win rate over 20 games vs agent_v10 determines which value is embedded in agent_v12 and propagated to agent_v15.

**Rationale**: No prior experiment has tested garrison sizing in isolation; the optimal value is unknown. Three data points bracket the plausible range cheaply (60 additional games total).

**Alternatives considered**: Bayesian search over a continuous range — overkill for a 20-game evaluation window where variance is high.

---

### D-004: Threat threshold for Candidate C

**Decision**: Dispatch defense only when `incoming_enemy_ships > current_garrison + production × 5`.

**Rationale**: `production × 5` represents ~5 turns of self-replenishment. If the garrison can recover before the fleet arrives, no reinforcement is needed. This directly addresses the over-triggering that caused agent_v6's defensive drag (`experiments/2026-05-29-defensive-reinforce.md`).

**Alternatives considered**: `production × 3` (too sensitive), `production × 10` (may under-protect low-production planets).

---

### D-005: Single-sender selection metric (Candidate D)

**Decision**: `efficiency = distance / available_ships_surplus` where `available_ships_surplus = current_ships − garrison_floor`. Lowest score wins the right to attack the target.

**Rationale**: Balances proximity (speed to impact) against surplus (cost to send). A planet 10 units away with 5 surplus ships (efficiency 2.0) is favored over one 5 units away with 2 surplus ships (efficiency 2.5).

**Alternatives considered**: Pure distance — ignores capacity. Pure surplus — ignores travel time. Product `distance × 1/surplus` is equivalent; ratio form is more readable.

---

### D-006: Mechanic integration order in agent_v15

**Decision**: Apply mechanics in this order each turn:

1. Defense pass (C): scan owned planets for threats, dispatch reinforcements if threshold exceeded
2. Offense pass — for each enemy/neutral target:
   a. Single-sender filter (D): skip if this planet is not the best sender for the target
   b. Redundancy check (A): skip if target already has sufficient en route coverage
   c. Fleet size (B): send `min(target.ships + 1, available_ships)` from the garrison-floored surplus

**Rationale**: Defense is time-critical and should not be gated by offensive coordination logic. Offense coordination (D→A→B) flows from target selection down to fleet sizing.

**Interaction guards**:
- Defense dispatch (C) bypasses the single-sender check (D) entirely.
- If garrison floor (B) leaves zero surplus, neither offense nor defense fires from that planet.

---

### D-007: Diagnostic scope

**Decision**: Run `diagnose_v9.py` only on agent_v15 (combined), not on individual candidates.

**Rationale**: SC-004 requires zero sun/OOB losses on the combined agent. Candidates inherit agent_v10's safety guards and are not modifying path-safety logic, so individual diagnostic runs add cost without new signal.

**Alternatives considered**: Running diagnostics on all candidates — adds 80 game-runs; rejected as low-value given the safety guards are unchanged.

---

## Known Risks

| Risk | Likelihood | Mitigation |
| ---- | ---------- | ---------- |
| No candidate reaches 55% | Low — each mechanic targets a documented waste pattern in v10 | Document all results, re-hypothesize for next round |
| Mechanic interaction regression in v15 | Medium — D+B together restrict firing aggressively | Test subsets if v15 < 65%; isolate conflicting pair |
| Candidate C recreates agent_v6 over-defense | Low — `production × 5` threshold is materially stricter than v6's `incoming > garrison` | Monitor turns-on-defense ratio during eval run |
| Garrison floor (B) too high → starvation | Low-Medium | Cap floor at `min(production × N, planet.ships // 2)` so a planet never locks all its ships |

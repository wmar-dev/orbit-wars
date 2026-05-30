# Research: Agent Improvement Experiments — Round 3

**Branch**: `007-more-agent-experiments` | **Date**: 2026-05-30

## Prior Round Summary

| Round | Agents | Baseline | Passing Mechanics | Combined Result |
|-------|--------|----------|-------------------|-----------------|
| 1 (005) | v11–v14 | v10 | Candidate D (single-sender, 70%) | v15: 70% vs v10 |
| 2 (006) | v16–v19 | v15 | Candidate E (orbit-lead fix, 70%), Candidate H (ROI scoring, 60%) | v20: 75% vs v15 |
| **3 (007)** | **v21–v24** | **v20** | TBD | **v25: target ≥65% vs v20** |

### Failed Mechanics (do not retry without revised hypothesis)

| Candidate | Round | Win rate | Failure reason |
|-----------|-------|----------|----------------|
| A (redundant fleet avoidance) | 1 | 10% | Wasted turns on duplicate dispatches |
| B (garrison sizing with floor) | 1 | 0% | Over-conserved ships, missed captures |
| C (threat-aware defense) | 1 | 10% | Too broad — defended every threat, starved offense |
| F (transit-adjusted fleet sizing) | 2 | 15% | Skip-if-can't-afford caused indefinite stalls |
| G (adaptive range expansion) | 2 | 0% | Hard thresholds (1.5×→3.5, 0.7×→1.5) caused extreme contraction |

---

## Decision Log

### D-001: Reactive Defense (Candidate I)

**Decision**: Trigger only on *certain-loss* situations (projected garrison < incoming fleet ships at arrival). Only reinforce if a nearby source has enough surplus.

**Rationale**: Candidate C failed because it defended any threat, even ones the garrison could absorb. Candidate I is narrower: fires only when the planet will definitely fall and a reinforcement can actually save it.

**Alternatives considered**:
- Broad defense (Candidate C pattern): Rejected — proven failure at 10%.
- Preemptive defense (reinforce before threat arrives): Too speculative; would consume offensive turns on hypothetical threats.

**Fleet observation**: `obs.get("fleets", [])` in orbit_wars returns fleets as dicts with keys `owner`, `ships`, `destination`, `distance_remaining`. Verified via kaggle_environments source. If key absent, defense is skipped silently.

### D-002: Smooth Adaptive Range (Candidate J)

**Decision**: `range_factor = clamp(2.0 * ratio ** 0.25, 1.5, 3.5)` where `ratio = own_total / max(1, enemy_total)`.

**Rationale**: Candidate G used step-function thresholds (ratio ≥ 1.5 → 3.5, ratio ≤ 0.7 → 1.5, else 2.0) and scored 0% vs v15. The contraction to 1.5 at ratio ≤ 0.7 was catastrophic — when losing, the agent couldn't reach any targets. The power-law `** 0.25` is much gentler: at ratio = 0.5 (badly losing), range_factor = 2.0 × 0.5^0.25 ≈ 1.68 (mild contraction). At ratio = 2.0 (winning), range_factor ≈ 2.38 (mild expansion).

**Alternatives considered**:
- Candidate G exact retry: Rejected (identical hypothesis = identical failure).
- Linear interpolation: Rejected — linear goes negative at extreme loss ratios.
- No range adjustment: Status quo (RANGE_FACTOR = 2.0) — this is the control.

### D-003: Enemy-Territory Priority (Candidate K)

**Decision**: Multiply ROI score by 1.5 for enemy-owned targets when `own_total / enemy_total ≥ 1.5`.

**Rationale**: The current ROI formula treats neutral and enemy planets identically. When significantly winning, capturing enemy production centers ends the game faster than neutral expansion. A 1.5× multiplier is conservative enough to not ignore high-ROI neutrals but tips the balance toward enemies when it matters.

**Alternatives considered**:
- Always boost enemy planets: Risk of over-aggression when losing; rejected.
- Reduce neutral score (penalty): Equivalent effect but harder to tune without disrupting existing scores.

### D-004: Two-Source Coordinated Attack (Candidate L)

**Decision**: Allow exactly 2 sources to jointly attack one target no single source can afford. Each sends `ceil(needed / 2)`. Only if both sources are within `range_factor` of the target.

**Rationale**: Single-sender coordination (Candidate D, the current backbone) permanently skips targets no single planet can afford. Large enemy strongholds are therefore permanently unreachable, even when two nearby planets together could flip them.

**Alternatives considered**:
- 3-source coordination: Too complex, risk of over-commit from 3 directions simultaneously.
- Remove single-sender entirely: Reverts to old behavior that over-committed from weak positions; proven worse than single-sender.

**Interaction with single-sender**: Single-sender runs first. Two-source only activates for targets *already excluded by single-sender* due to affordability (i.e., `mine.ships - garrison_floor < target.ships + 1` for all single sources).

### D-005: 4-Player Mechanics (Candidates M and N)

**Decision**: Both M (neutral-first when losing) and N (focus-fire on leader) are gated by player count. In 2-player, N degenerates to Candidate K (enemy priority). Both are included only in the combined agent (v25), not tested in isolation as 2P candidates.

**Rationale**: Testing M and N in 2-player mode would not reflect their intended use case. A separate 4P eval protocol (eval4.py, 20 games vs 3× random) validates their contribution.

**4-player map differences**:
- More planets (typically 12–16 vs 8–10 in 2P)
- More starting distance between players
- Neutral buffer zones are larger
- Multi-directional threat: defending one flank leaves others exposed

**Garrison floor in 4-player**: Increase `GARRISON_FLOOR_FACTOR` from 5 to 7 for 4P-gated mechanics. Rationale: 3 opponents instead of 1; higher base garrison absorbs early multi-directional pressure without requiring active defense.

### D-006: eval4.py Harness Design

**Decision**: Create eval4.py based on eval.py. Places test agent in slot 0, opponents in slots 1–3. Metrics: rank, win rate (rank 1), mean elimination turn.

**CLI**: `python eval4.py --agent agent_vN.py --opponent random --games 20`

**Opponent configurations**:
1. `--opponent random` (default) — 3 random opponents, establishes absolute baseline
2. `--opponent agent_v20.py` — 3× agent_v20, measures improvement in competent 4P field

**Rank metric**: rank = number of opponents who outlasted the agent + 1. Winner = rank 1.

**Pass criterion for 4P mechanics**: average rank ≤ 2.0 vs 3× random (expected rank of random agent = 2.5, so rank ≤ 2.0 shows clear improvement).

### D-007: Leaderboard Regression Diagnosis

**Hypothesis A** (most likely): Single-sender coordination reduces aggression. In 4-player, passive play lets 3 opponents outpace you. Test: compare v8 vs v20 average rank in eval4.py.

**Hypothesis B**: Safety guards over-filter in complex 4P maps. Test: count filtered moves (add diagnostic counter) and compare v8 vs v20.

**Hypothesis C**: ROI formula discounts distant planets too heavily. In 4P maps (more spread), most high-production planets are far away. Test: compare target-selection histograms between v8 and v20 over 4P games.

**Action**: Run `python eval4.py --agent agent_v8.py --opponent random --games 20` and `python eval4.py --agent agent_v20.py --opponent random --games 20` to measure the actual rank gap before implementing fixes.

---

## Open Questions

None — all NEEDS CLARIFICATION resolved.

- Fleet observation structure: Confirmed (`obs.fleets` or `obs.get("fleets", [])`)
- 4-player player count detection: Infer from unique non-negative owners in `obs.planets`
- Garrison floor for 4P: 7 (vs 5 for 2P); verified doesn't over-conserve on typical map sizes

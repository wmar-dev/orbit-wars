# Research: Agent Experiments Round 3

**Date**: 2026-06-06 | **Branch**: `023-agent-experiments-round-3` | **Spec**: `specs/023-agent-experiments-round-3/spec.md`

## Decision: Baseline Control

**Decision**: All experiments evaluated against v62 (current best agent), not v60.

**Rationale**: Testing against v62 tells us if each experiment actually improves our best agent. v60 is outdated — v62 already beats it 72%. Improvements additive to v62 are what matter for Kaggle leaderboard movement.

**Alternatives considered**: v60 baseline (would measure against outdated agent, results not actionable).

---

## Decision: Agent File Structure

**Decision**: Create `agent_v63.py` as copy of v62 + new experiment toggles. v62 remains frozen as baseline.

**Rationale**: Consistent with v60→v61→v62 pattern. Keeps clear version history. Each experiment is independently togglable.

**Alternatives considered**: Adding toggles to v62 in-place (would lose clean baseline reference).

---

## Decision: Defense Interceptor Evaluation

The `DEFENSE_INTERCEPT_ENABLED` toggle already exists in v62 (lines 430–502 in `_greedy_moves()`). It's a pre-pass that:

1. Scans all enemy fleets for angle-matches to allied planets
2. Computes `garrison_at_arrival = current_ships + production × eta`
3. If `fleet_ships > garrison_at_arrival × INTERCEPT_MIN_THREAT_RATIO (1.2)`, marks the planet as threatened
4. Finds nearest allied source that can reinforce before the enemy fleet arrives
5. Checks the source can afford the intercept without dropping below its garrison floor
6. Dispatches the intercept move

**Evaluation**: Copy v62 to v63, then run `v63 (intercept ON) vs v63 (intercept OFF)`. The `--swap` flag ensures both sides play each configuration an equal number of times.

---

## Decision: Deep Search Timing

The current beam search iterates candidates, simulates `SEARCH_DEPTH` steps each, and picks the best score. The search budget is 800ms per turn.

**Key constraint**: `eval.py` does not currently collect per-turn timing data. FR-003 requires adding timing instrumentation to the eval harness (p50/p95/p99).

**Depth scaling**: Each additional depth step adds one full `_SimState.step()` call per candidate. At SEARCH_DEPTH=10, K=3, there are ~30 simulation steps per turn (10 candidates × 10 steps / 3 branches). At depth=15, this becomes ~45 steps (same candidates × 15 steps). The simulator is fast (pure Python math, no allocations) so the scaling is roughly linear.

**Approach**: Profile current depth=10 timing first, then test depth=15. If timing exceeds p95 < 780ms, reduce BEAM_K (e.g., K=2 at depth=15) to keep the number of simulated steps manageable.

---

## Decision: Corrected Weighted Eval

**Root cause of v61 failure (40% win rate)**: The v61 cumulative scoring accumulated `TRANSIT_WEIGHT × fleet_ships` in EVERY intermediate step before fleets arrived. Since fleets typically take 5–9 turns to arrive at depth=10, a dispatch candidate got 5–9 extra "in-transit bonus" steps compared to the hold candidate (which had no fleets). This systematically inflated the score of dispatch-heavy candidates, causing the beam search to over-dispatch and lose.

**Fix**: Accumulate only production differential (`own_prod - opp_prod`) during intermediate steps. Apply transit weight only at the final (horizon) step. This way:
- Production advantage from capturing a planet early IS rewarded (accumulated over remaining steps)
- In-transit fleets don't get spurious bonus points
- The horizon evaluation remains identical to the current approach when no captures occur mid-simulation

**Implementation sketch**:
```python
if WEIGHTED_EVAL_FIXED_ENABLED:
    score = 0.0
    for _ in range(SEARCH_DEPTH):
        state.step(opponent_model=..., player=...)
        # Accumulate production differential only (no transit weight)
        own_prod = sum(p.production for p in state.planets if p.owner == player)
        opp_prod = sum(p.production for p in state.planets if 0 <= p.owner != player)
        score += (own_prod - opp_prod)
    # Add transit weight and enhanced eval at the horizon only
    score += TRANSIT_WEIGHT * (own_transit - opp_transit)
    if EVAL_ENHANCED_ENABLED:
        score += PLANET_COUNT_WEIGHT * (own_planets - opp_planets)
        score += SHIP_COUNT_WEIGHT * (own_ships - opp_ships)
```

---

## Timings Baseline

Initial self-play test (5 games, v62 vs v62) confirmed the eval harness runs correctly. Per-turn timing data will be collected once FR-003 timing instrumentation is added. The existing `t_start` variable in `agent()` and the `time.perf_counter() - t_start` check in `_beam_search` can be leveraged to collect timing without significant overhead.

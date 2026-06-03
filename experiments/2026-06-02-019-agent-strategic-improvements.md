# Experiment: Agent Strategic Improvements — Coordination, Defense, Beam Search

**Date**: 2026-06-02
**Branch**: 019-agent-mcts-coordination-defense
**Base agent**: agent_v58.py (58% vs v57, 50 games)

## Background

Current best agent (v58) scores ~828–853 on Kaggle. The ceiling for greedy 1-ply play is ~850–900.
Three improvements target the gap to 1000:
1. Fleet coordination — eliminate redundant dispatches
2. Defensive reinforcement — respond to incoming enemy fleets
3. Beam search — evaluate multiple candidate action sets using a forward simulator

Timing baseline: v58 runs 0.29ms avg per turn; 1-second budget allows 200+ beam search candidates.

---

## Experiment A: Fleet Coordination

**Variant**: `agent_v59_coord.py`

**Hypothesis**: Eliminating redundant fleet dispatches (two mines sending to the same already-covered neutral) will free ships for additional captures and improve early-game efficiency.

**Change**: Added `coverage` dict that tracks in-transit own fleet ships per target. Dispatch check: if `coverage[target] >= ships_needed`, skip. After dispatch, record `coverage[target] += ships_needed`.

**Self-play result (vs agent_v58)**:
- Games: 50
- Win rate: **54.0%** (27W/23L)
- Notes: Modest improvement. Coverage dict prevents double-dispatch to already-covered targets.

**Conclusion**: PASS — +4pp vs v58. Include in combined agent.

---

## Experiment B: Defensive Reinforcement

**Variant**: `agent_v59_defense.py`

**Hypothesis**: Responding to detected incoming enemy fleets (when reinforcement can arrive in time and the planet's production justifies the cost) will reduce planet losses and improve mid-game resource advantage.

**Change**: Added `_threat_eta()` helper and `_defense_pre_pass()` that runs before `best_sender`. For each threatened owned planet with `production >= 2.0`, dispatches reinforcement from the nearest allied planet that can arrive in time while maintaining garrison.

**Self-play result (vs agent_v58) — initial (bugged)**:
- Games: 50
- Win rate: 26.0% — severe regression
- Bug: `needed` ignored planet growth during ETA; DEFENSE_MIN_PRODUCTION=2.0 too low; no cap on needed vs source ships

**Self-play result (vs agent_v58) — fixed**:
- Games: 50
- Win rate: **54.0%** (27W/21L/2D), score **56.0%**
- Fixes: correct formula `incoming - (p.ships + p.production * eta) + 1`; raised `DEFENSE_MIN_PRODUCTION` to 3.0; capped `needed` at 50% of source ships

**Conclusion**: PASS after fix — include in combined agent.

---

## Experiment C: Beam Search

**Variant**: `agent_v59_beam.py`

**Hypothesis**: Evaluating ~30 candidate action sets through a 5-turn forward simulation and selecting the one with the highest projected production advantage will produce better coordinated multi-planet decisions than 1-ply greedy.

**Change**: Added `_SimState` forward model, `_gen_candidates()` (greedy baseline + per-planet swaps + swarm variants + hold-all), and `_beam_search()` wrapper with 800ms timeout guard.

**Self-play result (vs agent_v58)**:
- Games: 50
- Win rate: **8.0%** (4W/0L/46D), score **54.0%**
- Notes: Mostly draws (same greedy decisions); beam only helps the 8% of games where holding a mine's dispatch leads to better outcome in 15-turn sim. Original implementation (wrong angles + garrison drain) scored 0%; simplified to greedy-subset-only approach restored correctness. The "subset" beam decides which mines dispatch vs. hold this turn.

**Conclusion**: Marginal improvement (score 54%). Include in combined but don't rely on it heavily.

---

## Experiment D: Combined Agent

**Variant**: `agent_v59.py`

**Selection**: All three improvements active.

**Self-play result (vs agent_v58)**:
- Games: 50 (initial) → 200 (confirmation)
- Win rate: 58.0% at 50 games → **50% at 200 games**
- Notes: 50-game result was variance. 200-game confirmation shows no improvement over v58. All three improvements (coord, defense, beam) are individually marginal and do not combine for a meaningful gain.

**Conclusion**: FAIL — v59 is statistically equivalent to v58. Do not submit. v58 remains the best agent. The coordination, defense, and beam search improvements as implemented do not measurably improve win rate against v58.

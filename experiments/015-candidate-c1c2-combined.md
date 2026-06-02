# Experiment 015: C1 + C2 Combined — ROI Mismatch Fix + Endgame Normalization

**Date**: 2026-06-01
**Base agent**: agent_v48.py (C1)
**Candidate agent**: agent_v55.py
**Target**: ≥56% win rate vs agent_v47 (200 games, ±3.5% CI at 95%)

## Motivation

C1 (agent_v48, 54% vs v47) and C2 (agent_v49, 48% vs v47) both modify `_roi` and
were individually below the 56% threshold. C1's experiment note flagged them as
potentially complementary. This run tests whether the combination passes.

## Changes (relative to agent_v47)

**C1**: `_roi` accepts `actual_fleet_size=None`; enemy candidates pre-processed
through `_enemy_fleet_size` before scoring so travel time uses the real (faster)
fleet speed. ROI no longer underestimates enemy-target attractiveness.

**C2**: `_roi` accepts `remaining_turns=100.0`; `agent()` computes
`game_remaining = max(1.0, 500.0 - step)` and threads it into every `_roi` call.
Late-game, far targets are penalized for low remaining production time.

## Self-play result

Win rate vs agent_v47: **41.5%** (83W / 117L / 0D) — 200 games, ±3.5% CI at 95%

Upper bound of 95% CI: ~45%. Unambiguously below parity.

## Conclusion

**FAIL** — clear regression. Individual results were 54% (C1) and 48% (C2); combined
is 41.5%, worse than either alone. The two changes interact destructively:

C1 pre-processes enemy candidates with corrected fleet speeds, changing which targets
win ROI selection. C2 then applies time-decay that re-ranks those same targets based
on remaining game turns. The re-ranking undoes C1's correction: enemy targets (which
need larger, faster fleets) have shorter travel times post-C1, but C2's penalty on
distant targets disproportionately hits the high-production enemy planets that C1 was
trying to elevate. The net effect is that enemy planets are suppressed twice.

**Both candidates ruled out** — individually (54%, 48%) and in combination (41.5%).
Neither clears the 56% threshold at any sample size with these confidence intervals.

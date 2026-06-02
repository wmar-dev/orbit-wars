# Experiment 015: Candidate 1 — ROI Scoring Mismatch Fix

**Date**: 2026-06-01
**Base agent**: agent_v47.py
**Candidate agent**: agent_v48.py
**Target**: ≥56% win rate vs agent_v47 (50 games)

## Hypothesis

After v47 fixed fleet sizing for enemy planets (dispatching `ships_needed = target.ships + production × travel + 1` instead of `target.ships + 1`), the ROI formula still uses `fleet_speed(target.ships + 1)` to estimate travel time. Enemy targets require a larger fleet, which travels faster, so their actual travel time is shorter than the ROI formula computes. This makes enemy targets appear less attractive than they are, biasing target selection toward neutrals.

Fix: pass `actual_fleet_size = ships_needed` into `_roi` for enemy targets so travel time reflects the fleet actually dispatched. For neutrals, behavior is unchanged (`ships_needed = target.ships + 1`).

## Change

Modified `_roi(t, bx, by, mine, actual_fleet_size=None)` to use `fleet_speed(actual_fleet_size)` when provided. Pre-compute `ships_needed` (and corrected orbit-lead position) for all enemy candidates before ROI scoring. Pass `actual_fleet_size=ships_needed` to `_roi` for enemy targets.

## Self-play result

Win rate vs agent_v47: 54% (27W/23L/0D) — below the 56% threshold

## Conclusion

FAIL — 54% win rate is below the 56% passing threshold and is not statistically distinguishable from 50% at 95% confidence (50-game sample ±7%). The direction is positive (enemy targets correctly scored with faster fleet speed), but the signal is too weak on its own. May combine with C2 (endgame normalization) since both modify _roi and their effects could be complementary.

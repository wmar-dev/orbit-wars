# Experiment 015: Candidate 4 — Sender Pre-Screening for Enemy Targets

**Date**: 2026-06-01
**Base agent**: agent_v47.py
**Candidate agent**: agent_v51.py
**Target**: ≥56% win rate vs agent_v47 (50 games)

## Hypothesis

The sender assignment loop picks the planet with best `dist / surplus` ratio for each target. For enemy targets, the actual `ships_needed` (production-adjusted) may exceed the chosen sender's total garrison, causing the attack to be silently dropped later. No fallback sender gets a chance. This loses offensive opportunities that could be covered by a different planet.

Fix: during sender selection, for enemy targets compute a rough `ships_needed` using the current (non-orbit-lead) target position and exclude senders whose `src.ships < rough_needed`. If no sender qualifies, the attack remains deferred (same as current behavior). If a different sender qualifies, that sender takes the assignment.

## Change

In `best_sender` inner loop, after the `surplus <= 0` guard: for `t.owner != -1`, compute `rough_needed = int(t.ships + t.production * (dist / fleet_speed(t.ships + 1))) + 1`; skip `src` if `src.ships < rough_needed`.

## Self-play result

Win rate vs agent_v47: 16% (8W/42L/0D) — severe regression

## Conclusion

FAIL — significant regression (16%). The pre-screening blocks senders too aggressively. Enemy planets early in the game often have garrisons of 20-50+ ships with production 3-5; the rough_needed estimate (ships + production × travel) is frequently larger than any single sender's garrison, preventing ALL attacks on enemy planets. The agent falls back to only targeting neutrals, while v47 can attack enemy planets via smaller fleets that at least deal damage. Removing this candidate entirely from consideration for the combined agent.

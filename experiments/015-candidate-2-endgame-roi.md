# Experiment 015: Candidate 2 — Endgame ROI Normalization

**Date**: 2026-06-01
**Base agent**: agent_v47.py
**Candidate agent**: agent_v49.py
**Target**: ≥56% win rate vs agent_v47 (50 games)

## Hypothesis

The ROI time-decay term uses a hardcoded `max(1.0, 100.0 - travel)`. In the last 100 turns of a 500-turn game, this overestimates the value of distant targets — a planet 40 travel-turns away has only `remaining_turns - travel` turns of production, not 60.

Fix: replace `100.0` with `remaining_turns = max(1.0, 500.0 - step)`, passing it from `agent()` into `_roi`. Late-game, far targets are correctly penalized. Early-game (turns 0–400), the larger `remaining_turns` slightly inflates all ROI values but preserves relative ordering.

## Change

Modified `_roi(t, bx, by, mine, remaining_turns=100.0)` to use `max(1.0, remaining_turns - travel)` as the time-decay. Computed `remaining_turns = max(1.0, 500.0 - step)` in `agent()` and passed to every `_roi` call site.

## Self-play result

Win rate vs agent_v47: 48% (24W/26L/0D) — below the 56% threshold

## Conclusion

FAIL — 48% is within the noise band (±7% at 95% CI) and not meaningfully different from 50%. The hypothesis was directionally sound for late-game but the change has no effect when remaining_turns >= 100 (turns 0-400) since all ROIs scale proportionally and relative ordering is preserved via normalization. The late-game benefit may be too infrequent to show in a 50-game sample. May revisit if C1+C2 combined shows positive interaction; standalone C2 does not pass.

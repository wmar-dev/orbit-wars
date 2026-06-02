# Experiment 015: Candidate 6 — Persistent Campaign Target

**Date**: 2026-06-01
**Base agent**: agent_v47.py
**Candidate agent**: agent_v53.py
**Target**: ≥56% win rate vs agent_v47 (50 games)

## Hypothesis

The agent re-scores all targets from scratch each turn. ROI fluctuations (as ship counts and orbital positions change) can cause a planet to switch its assigned target turn-to-turn, sending partial fleets to multiple targets in sequence — none large enough to capture. A campaign target that persists across turns would prevent this flip-flopping.

Fix: module-level `_campaign` dict maps `planet_id → (target_id, roi_at_assignment)`. Each planet's campaign persists until: (1) target is captured by the player, (2) a friendly fleet already covers it, (3) a new target with >30% higher ROI appears. Otherwise the planet sticks to its campaign target without re-scoring.

## Change

Added module-level `_campaign = {}`. At turn start, prune campaigns for lost planets. Before sender assignment, if a planet has an active valid campaign, bypass normal scoring and assign directly to the campaign target. After dispatch, record `_campaign[mine.id] = (target.id, roi)`.

## Self-play result

Win rate vs agent_v47: 28% (14W/36L/0D) — severe regression

## Conclusion

FAIL — significant regression (28%). Campaign locking interacts badly with single-sender coordination: when a planet is locked to target A, other planets competing for A's assignment via normal scoring get excluded, while the locked planet may not have sufficient surplus. This creates coordination breakdown where neither planet attacks effectively. The campaign mechanism requires a fundamentally different sender assignment architecture (campaign-first, then fill remaining targets) rather than bolting on top of the existing dist/surplus scoring. Not suitable for the combined agent.

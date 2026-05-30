# agent_v33 Promotion — 009-fix-comet-fleet-targeting

**Date**: 2026-05-30

## Summary

Candidate R (production-squared ROI) passed the 55% gate with 60% score vs agent_v32 in
the primary evaluation. Incorporated into agent_v33 and confirmed in a second 50-game run.

## Candidate stacked

**Candidate R** — production-squared ROI: `(t.production ** 2) * max(1, 100-travel) / cost`

Why it passed on v32 but not v20:
- v20 had targeting bugs (2-iteration orbit-lead diverged for fast-orbiting planets)
- High-production planets are often orbiting, so fleets aimed at them frequently missed
- With converged orbit-lead in v32, these targets are now reliably intercepted
- Production^2 now delivers its intended benefit: decisive focus on the highest-value planets

## Confirm eval (50 games, agent0=v33, agent1=v32)

- Agent0 wins: 30
- Agent1 wins: 20
- Draws: 0
- Win rate: **60.0%**
- Score: **60.0%**
- Mean reward delta: see experiments/009-v33-promotion.jsonl

## Candidates NOT stacked

All 5 remaining retests failed or were inapplicable:
- P: superseded | J: inapplicable | K: 50% (50 draws) | L: 20% | I: 16%

## Next submission

agent_v33.py is the recommended Kaggle submission. Expected score improvement from 855.6
(v31 submission) based on: v32 bug fixes (64% vs v31) + Candidate R (60% vs v32).

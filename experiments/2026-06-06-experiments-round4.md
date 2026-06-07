# Experiment: Agent Experiments Round 4 (agent_v64)

**Date**: 2026-06-06 | **Branch**: `024-experiments-round-4` | **Agent**: `agent_v64.py`

---

## Overview

Three experiments on agent_v63 (52% vs v62, corrected weighted beam eval):

1. **P1** Improved opponent model v3 — production-weighted simulation to replace nearest-target surplus model
2. **P2** Multi-turn plan generation — skip candidates in beam search
3. **P3** Phase-detection dispatch — adjust params by game state

All experiments evaluated against **v63** as the baseline control (with v62 as secondary reference). Experimental agent is agent_v64.py.

---

## Baseline

- **Agent**: agent_v63.py (frozen, never modified)
- **Self-play baseline**: v63 confirmed at 52% vs v62 (from round 3). v64 with MULTI_TURN_PLAN_ENABLED(=True) at 54% vs v63.

---

## Direction 1: Opponent Model v3 (OPPONENT_MODEL_V3_ENABLED)

- **Hypothesis**: Replacing nearest-target surplus-only opponent model with production-weighted/ROI-based targeting will make beam search evaluations more accurate, improving tactical decisions against strong opponents like slawekbiel.
- **Change**: `OPPONENT_MODEL_V3_ENABLED=True` — all other toggles identical to v63
- **Self-play result**: 34.0% (17W/33L/0D, 50 games, --swap vs v63)
- **Timing**: p50=4.0ms p95=10.1ms p99=12.4ms
- **Conclusion**: **DISCARD** — 34% is well below 50% threshold. Making the simulated opponent more realistic with production-weighted targeting makes our beam search overly pessimistic. This is likely because the v2 model (nearest-target surplus) is a better approximation for early-mid game where opponents send to nearest planets anyway, and the realism of v3 suppresses our own dispatch aggression unnecessarily.

---

## Direction 2: Multi-Turn Plan Generation (MULTI_TURN_PLAN_ENABLED)

- **Hypothesis**: Adding "skip" candidates (zero dispatches for a turn) to the beam search will let the agent evaluate waiting-to-build vs immediate dispatch, enabling qualitatively different strategies.
- **Change**: `MULTI_TURN_PLAN_ENABLED=True` — all other toggles identical to v63
- **Self-play result**: 54.0% (27W/23L/0D, 50 games, --swap vs v63)
- **Timing**: p50=4.4ms p95=10.5ms p99=12.8ms
- **Conclusion**: **KEPT** — 54% exceeds the 52% threshold. Skip candidates add useful alternatives that the beam search can evaluate. When waiting is better (more ships → faster capture → higher score), the beam picks the skip; when immediate dispatch is better, it picks the normal dispatch.

---

## Direction 3: Phase-Detection Dispatch (PHASE_DETECTION_ENABLED)

- **Hypothesis**: Adjusting garrison floor and splinter window based on game phase (expansion/mid/elimination) will improve late-game conversion and win rate.
- **Change**: `PHASE_DETECTION_ENABLED=True` — all other toggles identical to v63
- **Self-play result**: 48.0% (24W/26L/0D, 50 games, --swap vs v63)
- **Timing**: Not recorded (US3 performance hit not relevant — discarded on win rate)
- **Conclusion**: **DISCARD** — 48% below the 50% threshold. The aggressive garrison floor reduction in elimination phase (0.7× multiplier) likely leaves planets vulnerable. Even the mid-game multiplier (0.85×) may free too many ships too early.

---

## Combined Configuration

- **Change**: `MULTI_TURN_PLAN_ENABLED=True` (only US2 passed)
- **Self-play result**: 54.0% (27W/23L/0D, 50 games, --swap vs v63)
- **Opponent sweep** (20 games each): sigmaborov 100%, dylanxue04 100%, yusufmurtaza 100%, slawekbiel 0% (no improvement)
- **Conclusion**: v64 (54% vs v63) is a genuine but small improvement (+2pp) over v63. Multi-turn planning works in theory but does not close the slawekbiel gap.

---

## Kaggle Submission

- **Score**: Not submitted — 54% vs v63 is an improvement but slawekbiel remains at 0%. Marginal improvement not worth a Kaggle submission vs v63.
- **Submission ID**: N/A

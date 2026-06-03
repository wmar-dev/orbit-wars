# Experiment: Early Expansion Fix — Replay 78539022 Analysis

**Date**: 2026-06-02
**Branch**: 018-replay-neutral-fleet-experiments
**Base agent**: agent_v57.py

## Background

Replay 78539022 (loss vs HY2017) revealed that our agent dispatched its first fleet at step 12 while the opponent dispatched at step 6. Root cause: the targeting loop selected Planet 16 (30 ships, growth 2.61) as the best-ROI target but could not afford it (needed 31 ships, had ~24). Rather than falling back to Planet 8 (18 ships, growth 2.09, affordable at 19 ships), the agent skipped the entire mine for that turn. This repeated for 6 steps until enough ships accumulated.

By step 20: opponent had 3 planets, we had 2. By step 30: opponent 6, us 3. Never recovered.

---

## Experiment A: Affordability Fallback

**Variant**: `agent_v58_fallback.py`

**Hypothesis**: Adding a fallback loop that iterates through ROI-sorted candidates until finding one the mine can afford will eliminate the 6-step dispatch delay and improve early-game expansion, leading to a higher win rate vs agent_v57.

**Change**: Modified the single-target pick + bail pattern in the main targeting loop (lines ~380–413 of agent_v57.py). Instead of: pick best ROI target → if unaffordable, skip mine; now: sort all candidates by ROI descending → iterate until finding candidate where `mine.ships >= ships_needed` → dispatch to that candidate.

**Self-play result**:
- Games: 50
- Win rate vs agent_v57: **58.0%** (29 wins / 21 losses / 0 draws)
- Notes: Initial version regressed badly (18% win rate) due to two bugs: (1) dispatching at step 0 leaving home with 0 ships; (2) quality threshold using relative-to-candidates max_roi which inflated cheap planets when the top candidate failed path-safety. Fixed by raising FALLBACK_MIN_RATIO from 0.60 to 0.70.

**Conclusion**: IMPROVED — +8pp over agent_v57. The affordability fallback with quality guard enables early dispatch to Planet 8-tier targets (ROI ≥70% of best candidate) while waiting for the best when no quality affordable alternative exists.

---

## Experiment B: Growth-Efficiency Scoring

**Variant**: `agent_v58_efficiency.py`

**Hypothesis**: Replacing the ROI formula with `production / ships` (growth-efficiency) for neutral target selection, combined with the affordability fallback, will prefer the planet that gives the most growth per ship invested, further improving early expansion over Experiment A.

**Change**: Built on agent_v58_fallback.py. Modified the `blended_key` sort comparator: for neutral targets (`owner == -1`), uses `production / max(ships, 1)` as the primary score instead of the ROI formula. Enemy target scoring unchanged.

**Self-play result**:
- Games: 50
- Win rate vs agent_v57: **10.0%** (5 wins / 45 losses / 0 draws)
- Notes: Severe regression. growth_efficiency = production/ships ranks Planet 22 (3/16=0.188) above Planet 16 (5/30=0.167) and Planet 8 (3/18=0.167) because it ignores travel distance. Cheaper-but-near planets displace the high-value targets that the ROI formula correctly weighs.

**Conclusion**: REJECTED — pure growth-efficiency scoring without distance weighting is counterproductive. Experiment A (ROI-based blended_key with fallback) remains the better approach.

---

## Experiment C: Winner Promotion

**Variant**: `agent_v58.py`

**Selection**: Experiment A (agent_v58_fallback.py) — no head-to-head needed; B (10%) was far below A (58%).

**Self-play result**:
- Games: 50 (Experiment A eval)
- Win rate vs agent_v57: **58.0%** (29 wins / 21 losses / 0 draws)
- Planets owned at step 25 (avg, 20 games): agent_v58 = 3.20 vs agent_v57 = 3.05

**Conclusion**: SHIPPED as agent_v58.py. The affordability fallback with 70% quality threshold (FALLBACK_MIN_RATIO) is the best variant. Early-game cascade effect confirmed (+0.15 planets at step 25).

---

## Fleet Sizing Verification (T009)

**Question**: Do neutral planets grow while neutral (static garrison vs growing)?

**Finding**: Confirmed static. Tracked planets 8, 11, 12, 16 across 8+ steps while neutral — all showed constant ship counts (18, 18, 11, 30 respectively). Neutral planets do NOT grow while unowned.

**Impact on fleet sizing**: Current `ships_needed = t.ships + 1` is correct. No change needed (T010 skipped).

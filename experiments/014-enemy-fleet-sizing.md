# Experiment 014: Enemy Fleet Sizing + Neutral ROI Fix

**Date**: 2026-05-31
**Base agent**: agent_v42.py
**Target**: ≥56% win rate vs agent_v42 (50 games)

---

## Background: Game Engine Analysis

Reading the orbit_wars game engine source (`orbit_wars.py`) revealed two mechanics that informed this round:

1. **Production is owner-gated** (line 514): `if planet[1] != -1: planet[5] += planet[6]`
   — Neutral planets (`owner == -1`) have **static garrison**. Only owned planets accumulate ships each turn.

2. **Combat uses arrival-time garrison**: production happens before fleet movement each tick, so an enemy planet with production P accumulates `P × travel_turns` ships while our fleet is in transit.

**Bug confirmed**: sending `target.ships + 1` ships against an ENEMY planet is always wrong for non-trivial travel distances. The enemy garrison grows during travel; our undersized fleet deals damage but fails to capture.

**No bug for neutrals**: `target.ships + 1` is correct for neutrals (static garrison). Captures succeed.

---

## Round 1 Candidates (all failed)

| Candidate | Change | Win Rate vs v42 | Notes |
|-----------|--------|-----------------|-------|
| v43 | Multi-fleet dispatch (send to ALL assigned targets per turn) | 6% (3W/47L) | Captures many planets at once, each with 1-ship garrison; enemy systematically recaptures weakly-defended planets |
| v44 | Race filtering (skip neutral if enemy fleet arrives first) | 44% (21W/27L/2D) | False positives: fleet heading toward neutral A may also point at neutral B (further along same angle); filters valid targets incorrectly |
| v45 | Urgency-weighted ROI for neutrals (boost if we're closer than enemy planet) | 52% (26W/24L) | Noise level; no significant improvement |

**Analysis**: Multi-fleet dispatch (v43) fails by the same mechanism as Candidate L (two-source attack): rapid over-expansion creates a patchwork of weakly-defended planets. Race filtering (v44) has a geometry problem — fleet angles are not planet-specific. Urgency boost (v45) is a weak signal.

---

## Round 2 Candidates

### Candidate A: ROI Denominator Fix for Neutrals (v46) — FAIL

**Change**: `_roi` denominator switches from `t.ships + t.production * travel + 1` to `t.ships + 1` for neutral planets (since their garrison is static).

**Hypothesis**: the `production * travel` cost term in the denominator was over-penalizing high-production neutrals far away, causing us to miss high-value targets.

**Result**: 20% (10W/40L) vs agent_v42 — **significant regression**.

**Post-mortem**: The original denominator was NOT a garrison estimate — it was an empirically-tuned distance-weighted value proxy. Removing the `production * travel` term for neutrals causes the agent to assign near-identical ROI to nearby vs distant neutrals (only the decay term `100 - travel` differentiates them, which is weak). The agent starts chasing high-production neutrals far away instead of efficiently capturing nearby ones. The original formula was correct-by-experiment, not correct-by-mechanics.

---

### Candidate B: Production-Adjusted Fleet Sizing for Enemy Planets (v47) — **PASS**

**Change**: when the best target is enemy-owned (not neutral), compute the garrison at estimated arrival:
  ```python
  travel = dist / fleet_speed(target.ships + 1)
  ships_needed = int(target.ships + target.production * travel) + 1
  ```
  Then recompute the orbit-lead with the corrected fleet speed (larger fleet = faster = different arrival position for orbiting planets).

**Hypothesis**: we've been sending undersized fleets to enemy planets. The fleet damages but fails to capture. By sending the correct fleet size, we'd actually capture enemy planets instead of just poking them.

**Result**: 68% (34W/16L) vs agent_v42 — **major improvement**.

| Eval | Win Rate | Record | Notes |
|------|----------|--------|-------|
| v47 vs agent_v42 | 68% | 34W/16L/0D | Primary eval |
| v47 vs agent_v38 | 72% | 36W/14L/0D | vs historic baseline |
| v47 vs agent_v47 | 50% score | 0W/0L/20D | All draws — symmetric optimal play |

**Analysis**: The fix is decisive. Correctly sizing fleets for enemy planets changes the late-game dynamic: instead of fleets that damage but don't capture, we now reliably take enemy planets. The ROI formula already correctly scores enemy planets (using `ships + production * travel` in the denominator), so target selection was already good — the bug was only in the dispatch phase. Orbit-lead recomputation is important because the larger fleet travels faster, arriving at a different orbital position than predicted by the naive lead.

---

## Conclusion

**Winner**: agent_v47 with 68% vs agent_v42, 72% vs agent_v38.

**Promoted to new best agent**: agent_v47.py replaces agent_v42.py.

**What worked**:
- Production-adjusted fleet sizing for enemy (non-neutral) planets: fixes a real bug where fleets were sent too small to capture their targets. The fix requires recomputing the orbit-lead at the corrected (faster) fleet speed.

**What didn't work**:
- Multi-fleet dispatch: creates under-defended planets that the enemy recaptures.
- Race filtering: geometry false positives filter valid targets.
- Urgency-weighted ROI: signal too weak to move the needle.
- Neutral ROI denominator fix: the original formula was tuned-by-experiment, not a garrison estimate; changing it disrupts the calibrated ordering.

**Root cause insight**: The ROI formula was already correct — it computes `t.ships + t.production * travel` in the denominator, correctly pricing in garrison accumulation during travel. But the FLEET SIZE we sent was always `t.ships + 1`, ignoring that accumulation. This split — correct scoring, wrong sizing — is what v47 repairs.

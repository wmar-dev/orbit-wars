# Data Model: Early Expansion Experiments

**Feature**: 018-replay-neutral-fleet-experiments
**Date**: 2026-06-02

---

## Core Entities (from existing codebase)

### Planet (existing, `kaggle_environments.envs.orbit_wars.orbit_wars.Planet`)
- `id`: int — unique identifier
- `owner`: int — -1=neutral, 0=player0, 1=player1
- `x`, `y`: float — current position
- `ships`: int — current ship count
- `production`: float — growth rate (ships per step when owned; neutral planets do not appear to grow based on replay evidence)
- `radius`: float — physical size (affects launch position and path safety)

### Fleet (existing, raw tuple format)
- `[id, player, x, y, angle, source_planet_id, ships]`
- Travels at `fleet_speed(ships)` per step toward its angle

---

## New Scoring Entities

### AffordableCandidate
A filtered view of the targeting candidate list, used in Experiment A:
- `target`: Planet — candidate target planet
- `predicted_x`, `predicted_y`: float — lead-corrected interception position
- `roi_score`: float — existing `_roi(t, bx, by, mine)` value
- `ships_needed`: int — `t.ships + 1` for neutrals
- `affordable`: bool — `mine.ships >= ships_needed`

**Key invariant**: The targeting loop MUST select the highest-ROI target among `affordable=True` candidates, not among all candidates.

### GrowthEfficiencyScore (Experiment B)
A per-planet score used as an alternative primary sort key:
- `score = planet.production / planet.ships` for neutrals
- Higher is better: captures growth rate per unit cost
- Breaks ties by distance (shorter distance preferred)
- Fallback if `planet.ships == 0`: use `planet.production` alone

**Relationship**: AffordableCandidate can carry either `roi_score` or `growth_efficiency_score` depending on the variant.

---

## State Transitions

### Normal targeting flow (existing):
```
my_planet has surplus ships
→ compute candidates (all non-owned targets where this planet is best sender)
→ rank by ROI
→ pick best_target
→ if mine.ships >= ships_needed: dispatch
→ else: SKIP (bug)
```

### Fixed targeting flow (Experiment A):
```
my_planet has surplus ships
→ compute candidates (all non-owned targets where this planet is best sender)
→ rank by ROI, descending
→ iterate: pick next-best target
  → if mine.ships >= ships_needed: dispatch, break
  → else: continue to next candidate
→ if no affordable candidate: skip
```

---

## Experiment Variant Matrix

| Variant file | Base | ROI formula | Fallback | Notes |
|---|---|---|---|---|
| `agent_v57.py` | baseline | `_roi` | none | current agent |
| `agent_v58_fallback.py` | v57 | `_roi` | yes | Experiment A |
| `agent_v58_efficiency.py` | v57 | growth/cost | yes | Experiment B |
| `agent_v58.py` | v57 | `_roi` + efficiency blend | yes | Experiment C (best of A+B) |

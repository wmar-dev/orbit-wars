# Research: Agent Decision Experiments

**Branch**: `013-agent-decision-experiments` | **Date**: 2026-05-31

## Decision A: Target Scoring Formula

### Current agent_v38 formula

```
ROI(t, src) = t.production² × max(1, 100 - travel_turns)
               / max(1, t.ships + t.production × travel_turns + 1)
```
Plus a reward blend: `(1 - 0.1) × roi_norm + 0.1 × reward_estimate(t, ships_needed)`

**What it optimises for**: High-production targets that are close (decay term) and cheap to
capture (denominator). The quadratic production term gives outsized weight to production ≥ 4
planets.

**What it misses**:
- Does not cap by distance (will score a far cheap planet above a nearby expensive one if
  production² is large enough)
- The decay term `max(1, 100 - travel_turns)` bottoms out at 1 for distant planets —
  effectively ignoring distance past ~99 turns of travel. This range is unreachable in most
  games (map is 100×100, max travel ~140 units at speed 1.0, but fleets are faster).
  In practice this term rarely matters.
- The blend term (REWARD_ALPHA=0.1) adds small weight to "captures generate positive reward
  signal" heuristic from RL training runs — not tuned for heuristic play.

**Alternatives decided**:

| Variant | Formula | Hypothesis |
|---------|---------|------------|
| scoring-1 | ROI (current) | Control baseline |
| scoring-2 | `prod / (ships + 1)` | Tests whether ignoring distance captures high-prod planets faster early game |
| scoring-3 | ROI with distance gate `dist ≤ nearest_dist × 1.5` | Tests whether forcing proximity first speeds expansion |
| scoring-4 | `0.67 × prod_norm + 0.33 × (1 - dist_norm)` | Tests linear combination with normalised inputs (no quadratic) |

**Decision**: Test all four. Winning variant selected by 50-game eval.

---

## Decision B: Fleet Sizing Policy

### Current policy

```python
ships_needed = target.ships + 1
```

**What it misses**:
1. **Production accrual**: A planet producing 4 ships/turn with 20 ships at evaluation
   time will have 20 + 4×T ships when the fleet arrives after T turns. Sending 21 ships
   fails against a garrison of 40+.
2. **Race conditions**: If an enemy fleet (N enemy ships) is en route to the same neutral,
   the fleet that arrives with more ships wins. Sending `target.ships + 1` loses to any
   enemy fleet larger than 1 ship.

### Production accrual formula

```
travel_turns = distance / fleet_speed(ships_needed)  # single-pass approximation
ships_needed = target.ships + 1 + target.production × ceil(travel_turns)
```

One-pass approximation is accurate enough: the correction term `production × travel_turns`
grows slowly with fleet size since fleet_speed is logarithmic.

### Race-aware formula

An enemy fleet is "heading to target" if:
```
angle_diff(enemy_fleet.angle, atan2(target_y - fleet_y, target_x - fleet_x)) < RACE_EPSILON
```
`RACE_EPSILON = 0.2` radians (from feature 012 analysis).

If an enemy fleet qualifies:
```
turns_until_enemy_arrives = distance_fleet_to_target / enemy_fleet_speed
ships_at_arrival = target.ships + target.production × turns_until_enemy_arrives
ships_needed = max(current_formula, enemy_fleet.ships + ships_at_arrival + 1)
```

**Rationale for alternatives decided**:

| Variant | Formula | Hypothesis |
|---------|---------|------------|
| fleet-1 | `target.ships + 1` (current) | Control baseline |
| fleet-2 | production-buffered | Fixes the production accrual blind spot; costs more ships |
| fleet-3 | race-aware | Fixes simultaneous-send racing; also costs more ships |
| fleet-4 | production-buffered + race-aware | Combined — most accurate, most expensive |

**Key concern**: Sending more ships per capture means fewer planets captured overall if the
agent runs out of surplus. This is the core fleet-sizing trade-off. The eval will show if
the higher capture reliability outweighs the cost.

---

## Decision C: Garrison Floor

### Current value

`GARRISON_FLOOR_FACTOR = 3` → floor = `max(3 × production, incoming_threat_ships)`

**Why 3**: Candidate O tested `GARRISON_FLOOR_FACTOR = 3` vs the previous value and it
passed. It was not swept over a range. The value has been inherited unchanged since agent_v33.

**Trade-off landscape**:
- Floor too low (1×): Agent empties owned planets to attack; any enemy fleet captures them
  during the offensive window. Catastrophic on maps with close starting positions.
- Floor too high (5×+): Agent retains large garrisons but never has enough surplus to
  capture neutrals. Production advantage never converts to planet count.
- Optimal floor: Low enough to generate surplus quickly early game; high enough to survive
  counterattacks mid-game.

**Dynamic floor motivation**: The risk of under-garrisoning is highest in mid-to-late game
when the enemy has large fleets. Early game, both agents have few ships and close planets
can be taken with small fleets. A dynamic floor — low early, higher late — lets the agent
race to high-production neutrals early without sacrificing late-game safety.

**Sweep plan**:

| Variant | Floor | Expected outcome |
|---------|-------|-----------------|
| floor-1 | `max(1 × prod, threat)` | Likely fails vs aggressive enemy; high planet-loss rate |
| floor-2 | `max(2 × prod, threat)` | May free enough early surplus to win races |
| floor-3 | `max(3 × prod, threat)` (current) | Baseline control |
| floor-4 | `max(5 × prod, threat)` | Likely too conservative; low capture rate |
| floor-5 | Dynamic: factor = `1 + 3 × min(step/300, 1)` → 1 at step 0, 4 at step 300+ | Ramps up with game age |

---

## Decision D: Source Assignment Policy

### Current rule

`best_sender[target.id]` = the single owned planet with lowest `dist / surplus` score.
Only that planet dispatches to that target. All other owned planets skip this target.

**Why single-sender was adopted**: Earlier multi-sender attempts (Candidate L) had all
planets send to the same target, draining garrisons below safe levels and producing 16%
win rate. The single-sender rule was the correct fix for that failure mode.

**Why multi-sender could be reintroduced correctly**: The failure was "all planets send" —
not "multiple planets can optionally contribute if they have surplus." A surplus-gated
design where each potential sender checks its own floor independently avoids the 2022
failure mode.

### Surplus-gated design

```
For each target t (sorted by value, highest first):
  primary_sender = best_sender[t.id]  # existing single-sender logic
  primary_sender dispatches as normal

  # NEW: secondary senders
  for each other owned planet p (sorted by surplus descending):
    surplus_p = p.ships - floor(p)
    if surplus_p > MIN_CONTRIB (= 10):
      p sends MIN_CONTRIB ships to t  # small supplemental fleet
      p is not excluded from targeting OTHER targets this turn
```

**Key design constraint**: Secondary senders are not exclusive — they can still be the
primary sender for a different target. This prevents the "everyone ignores everything else
to pile on one target" failure mode of Candidate L.

**Top-2 sender alternative**:
```
For each target t:
  sender_1 = best_sender (current)
  sender_2 = second-best by dist/surplus (new)
  sender_2 dispatches if: sender_2.ships - floor(sender_2) >= target.ships / 2 + 1
  sender_1 sends target.ships / 2 + 2, sender_2 sends target.ships / 2 + 1
  (together they send slightly more than needed to capture)
```

**Variants decided**:

| Variant | Rule | Hypothesis |
|---------|------|------------|
| assign-1 | single best sender (current) | Control baseline |
| assign-2 | surplus-gated secondary senders (MIN_CONTRIB=10) | Delivers supplemental force to contested targets |
| assign-3 | top-2 senders with split cost | Enables coordinated capture of defended targets |

---

## Implementation Notes

### Variant file naming

Each variant file is a copy of agent_v38.py with one changed section:
```
agent_013_scoring_2.py    # scoring experiment, variant 2
agent_013_scoring_3.py
agent_013_scoring_4.py
agent_013_fleet_2.py      # fleet sizing experiment, variant 2
agent_013_fleet_3.py
agent_013_fleet_4.py
agent_013_floor_1.py      # garrison floor sweep
agent_013_floor_2.py
agent_013_floor_4.py
agent_013_floor_5.py
agent_013_assign_2.py     # source assignment experiment
agent_013_assign_3.py
```

(Variant "1" in each experiment = agent_v38 baseline = control, no separate file needed.)

### Eval command template

```bash
uv run python eval.py --agent0 agent_013_scoring_2.py --agent1 agent_v38.py --games 50 --seed 0
```

Record win rate and notes in `experiments/013-agent-decisions.md` after each run.

### Secondary metric collection

For the best variant per experiment (and for agent_v41 final eval), also capture:
- Planets controlled at step 100 (using `--verbose` flag or reward-log JSONL)
- Production rate at step 150

These help diagnose why a variant wins or loses.

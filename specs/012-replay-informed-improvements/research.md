# Research: Replay-Informed Agent Improvements

**Feature**: `012-replay-informed-improvements` | **Date**: 2026-05-31

All NEEDS CLARIFICATION items from the Technical Context resolved below.

---

## RES-001: agent_v38 Baseline Capability Audit

**Decision**: agent_v38 is a well-structured heuristic agent with modular helper functions. agent_v40 should be built as a copy of agent_v38 with targeted changes — not a rewrite.

**Findings**:

- 354 lines, all stdlib + `kaggle_environments.Planet` namedtuple import
- Single-sender coordination via `best_sender` dict: each target assigned exactly one source planet
- Scoring: blended ROI = `(1 - REWARD_ALPHA) * roi_norm + REWARD_ALPHA * reward_estimate`
- ROI formula: `production² × max(1, 100 - travel) / max(1, ships + production × travel + 1)`
- Threat detection (Candidate U) already present — enemy fleet angle matching, garrison floor raised
- Orbit-lead prediction already present (`_converged_orbit_lead`, `_comet_two_pass`)
- Path safety check already present (`_path_safe` — sun exclusion + planet obstruction)
- Garrison floor: `max(GARRISON_FLOOR_FACTOR * production, threat.get(src.id, 0))`

**Gap analysis** — what agent_v38 lacks vs Isaiah's strategy:

| Gap | Isaiah's Behaviour | agent_v38 Current | agent_v40 Fix |
| --- | ------------------ | ----------------- | ------------- |
| Planet priority | Targets high-production first | ROI-based (favours accessible planets) | Normalised value score with 2× production weight |
| Multi-planet coordination | 2–3 planets send to same target same turn | One sender per target | Top-target grouping model |
| Ship banking | Pauses attacks to accumulate fleet | Always spends surplus immediately | Banking mode gated on production advantage |
| Race contestation | Sends enough to win contested captures | Sends `target.ships + 1` regardless | Detects enemy fleets en route, scales up |

---

## RES-002: Value Function Design

**Decision**: Use a linear weighted sum of normalised production and distance scores.

```
planet_value(p, source) =
    PROD_WEIGHT * (p.production / MAX_PROD) - DIST_WEIGHT * (dist(source, p) / MAX_DIST)
```

Constants:
- `PROD_WEIGHT = 2.0`
- `DIST_WEIGHT = 1.0`
- `MAX_PROD = 5` (fixed per CONTEST.md — production is integer 1–5)
- `MAX_DIST = 141.4` (diagonal of 100×100 board = √(100²+100²))

**Why fixed MAX_PROD/MAX_DIST**: Using observed-map max causes instability at game start when only a few planets are visible. Fixed constants are stable and well-defined.

**Enemy planet scoring**: Same formula applies, but enemy planets get an additional factor:

```
enemy_value(p, source) = planet_value(p, source) - ENEMY_PENALTY * (p.ships / MAX_SHIPS_ESTIMATE)
```

`ENEMY_PENALTY = 0.5`, `MAX_SHIPS_ESTIMATE = 500` (soft cap — prevents overcommitting to heavily garrisoned planets).

**Alternatives considered**:

- Rank-based scoring: rejected — loses magnitude information, all production-5 planets rank the same regardless of distance
- Raw ROI (current agent_v38): rejected — production² term already favours high-production but distance dominates for close low-production planets

---

## RES-003: Multi-Planet Coordination Model

**Decision**: Top-target grouping with secondary assignment.

**Algorithm**:

```
1. Score all non-owned planets → sorted list by planet_value desc
2. primary_target = top of list
3. For each owned planet (sorted by surplus desc):
     if surplus > 0 and not departing/evacuating:
         send to primary_target (all surplus planets join the wave)
         mark planet as assigned
4. secondary_target = next uncontested target on list
5. For remaining unassigned planets with surplus:
     send to secondary_target using existing orbit-lead logic
```

**Why this over per-target best-sender**: Isaiah's replay shows wave attacks with 2–3 planets all sending at the same angle. The per-target model physically cannot produce this — it limits each target to one sender. Top-target grouping naturally produces the coordinated wave pattern.

**Interaction with banking mode**: When banking is active, step 3 is skipped entirely (no sends). Step 3 is also skipped for evacuation planets (existing logic preserved).

**Ship quantity per sender**: Each planet sends `ships_needed` where:

```
ships_needed = max(primary_target.ships + 1, primary_target.ships + enemy_incoming + 1)
ships_to_send = min(ships_needed, source.ships - garrison_floor)
```

If `ships_to_send <= 0`, that planet skips the send (does not join the wave).

---

## RES-004: Banking Phase State Machine

**Decision**: Banking phase is a per-turn stateless check (no persistent state needed between turns — the agent is stateless by design).

**State check function**:

```python
def _banking_mode(my_planets, enemy_planets, step, variant):
    my_prod = sum(p.production for p in my_planets)
    enemy_prod = sum(p.production for p in enemy_planets)
    prod_advantage = my_prod / max(enemy_prod, 1)
    my_ships = sum(p.ships for p in my_planets)

    if prod_advantage < BANK_PROD_THRESHOLD:  # 1.3
        return False

    if variant == "A":
        return my_ships < BANK_FIXED_THRESHOLD  # 800
    elif variant == "B":
        return my_ships < my_prod * BANK_TURNS_FACTOR  # my_prod * 25
    elif variant == "C":
        return step < BANK_STEP_CAP and my_ships < BANK_ADAPTIVE_THRESHOLD  # 200, 600
    return False
```

**What banking suppresses**: The main targeting/attack loop only. Evacuation logic (departing/expiring comets) runs regardless. Threat-aware garrison logic (Candidate U) runs regardless.

**Rationale for keeping evacuation active during banking**: Stranding ships on an expiring comet is always bad regardless of strategic phase.

---

## RES-005: High-Production Fallback Mode

**Decision**: Implement both variants A and C as a runtime flag; evaluate both.

**Variant A — Direct attack**:

```
if no neutral planets with production >= HIGH_PROD_THRESHOLD (4):
    targets = all enemy planets with production >= HIGH_PROD_THRESHOLD
    sort by planet_value desc (ignores garrison size)
    use top as primary_target
```

**Variant C — Hybrid**:

```
if no neutral planets with production >= HIGH_PROD_THRESHOLD (4):
    enemy_hp = min enemy high-production planet by (ships / production)  # most capturable
    neutral_targets = all neutral planets (any production)
    primary_target = enemy_hp
    secondary_targets = neutral_targets sorted by planet_value desc
    assign planets to primary/secondary as in normal grouping
```

**Evaluation**: Run 50 games each against agent_v38. Variant with higher win rate is hardcoded into agent_v40.

---

## RES-006: Race Condition — Enemy Fleet Detection

**Decision**: Reuse the existing `_angle_diff` + `ANGLE_EPSILON` pattern from Candidate U (threat detection) but apply it to neutral planet targets.

```python
RACE_EPSILON = 0.2  # radians — wider than ANGLE_EPSILON=0.1 for threat detection

def _enemy_incoming(target_x, target_y, raw_fleets, player):
    total = 0
    for f in raw_fleets:
        f_owner = f[1] if isinstance(f, (list,tuple)) else f.owner
        if f_owner == player:
            continue
        f_x = float(f[2] if isinstance(f,(list,tuple)) else f.x)
        f_y = float(f[3] if isinstance(f,(list,tuple)) else f.y)
        f_angle = float(f[4] if isinstance(f,(list,tuple)) else f.angle)
        f_ships = int(f[6] if isinstance(f,(list,tuple)) else f.ships)
        expected = math.atan2(target_y - f_y, target_x - f_x)
        if _angle_diff(f_angle, expected) < RACE_EPSILON:
            total += f_ships
    return total
```

**Wider epsilon (0.2 vs 0.1)**: Neutral targets are predicted positions (orbit-lead), not current positions. A wider epsilon accounts for lead prediction error.

---

## RES-007: Variant Naming and Eval Plan

**Variant flag constants** (in agent_v40 source, toggled at top of file for each eval run):

```python
BANKING_VARIANT = "B"   # "A", "B", or "C"
FALLBACK_VARIANT = "C"  # "A" or "C"
```

**Eval command** (for each variant):

```bash
python eval.py --agent0 agent_v40.py --agent1 agent_v38.py --games 50 --seed 0
```

**Results recorded in**: `experiments/012-replay-informed.md`

**Selection criteria**: Highest win rate vs agent_v38. Ties broken by average end-game ship count.

**Predicted best**: B-C (production-relative banking + hybrid fallback) based on replay analysis, but all 6 variants run regardless.

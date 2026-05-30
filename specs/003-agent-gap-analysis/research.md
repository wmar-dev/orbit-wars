# Research: Agent Gap Analysis

**Feature**: 003-agent-gap-analysis | **Date**: 2026-05-29

## R-1: Orbiting Planet Detection & Lead Calculation

**Decision**: Detect orbiting planets by checking if `distance_from_center < 50 - planet.radius` using `initial_planets` data. Compute predicted arrival position with a single-pass travel-time estimate.

**Rationale**: The CONTEST.md spec states planets orbit when `orbital_radius + planet_radius < 50`. `initial_planets` gives position at turn 0; combined with `angular_velocity` (constant per game), we can always reconstruct current angle and predict future angle. One-pass is sufficient because angular velocity (0.025–0.05 rad/turn) × typical travel time (5–15 turns) = 0.1–0.75 rad displacement — enough to miss a planet's radius (~1–3 units) at orbital radius ~20–40. Iterative refinement adds complexity for marginal gain.

**Alternatives considered**:
- Track current angle from current (x, y) each turn: equivalent to `atan2(y-50, x-50)`; works without needing `initial_planets`, but `initial_planets` is needed anyway to confirm orbital radius.
- Two-pass iteration: recompute distance to predicted position, refine T. Adds one function call per target with <5% accuracy gain given small angular velocities.

**Key formula**:
```
orbital_radius = hypot(ip.x - 50, ip.y - 50)   # from initial_planets
is_orbiting    = orbital_radius + planet.radius < 50
theta_now      = atan2(planet.y - 50, planet.x - 50)   # current angle
T              = hypot(planet.x - mine.x, planet.y - mine.y) / fleet_speed(ships)
theta_pred     = theta_now + angular_velocity * T
x_pred         = 50 + orbital_radius * cos(theta_pred)
y_pred         = 50 + orbital_radius * sin(theta_pred)
```

## R-2: Comet Path Prediction

**Decision**: Index into `comets[group].paths[path_index + T]` for predicted comet position. Skip if `path_index + T + 5 >= len(paths)` (5-turn expiry buffer).

**Rationale**: The `paths` field is the full precomputed trajectory. `path_index` is the current step. Travel turns T indexes directly into the remaining path — no trigonometry needed. The 5-turn buffer prevents sending a fleet at a comet that expires on or just after arrival (ships would garrison a comet that immediately departs, losing them).

**Alternatives considered**:
- Recompute comet position from elliptical orbit parameters: the `paths` array is already precomputed, making this redundant.
- Skip comets entirely from targeting: misses low-garrison captures worth 1 ship/turn production each.

**Data access pattern**:
```python
# Build lookup once per turn
comet_path_lookup = {}
for group in obs.comets:
    for i, pid in enumerate(group['planet_ids']):
        comet_path_lookup[pid] = (group['paths'][i], group['path_index'])

# In targeting loop
if target.id in comet_planet_ids:
    path, idx = comet_path_lookup[target.id]
    if idx + T + 5 >= len(path):
        continue  # comet leaving soon
    x_pred, y_pred = path[idx + T]
```

## R-3: Fleet Heading Detection for Defense

**Decision**: Reuse the dot-product alignment approach from `eval.py` verbose wrapper. A fleet is "heading toward" planet P if alignment score > 0.95 (within ~18° of direct heading).

**Rationale**: The engine uses continuous collision detection, so a fleet heading even slightly toward a planet will likely hit it within a few turns. 0.95 alignment (~18° cone) is conservative enough to avoid false positives from fleets passing near but not at a planet.

**Formula**:
```python
def _heading_toward(fleet, planet):
    dx, dy = planet.x - fleet.x, planet.y - fleet.y
    dist = hypot(dx, dy)
    if dist < 0.1:
        return True
    return (dx * cos(fleet.angle) + dy * sin(fleet.angle)) / dist > 0.95
```

## R-4: Fleet Speed Formula Verification

**Decision**: `fleet_speed(n) = 1.0 + 5.0 × (log(n) / log(1000))^1.5` confirmed from CONTEST.md.

Reference values:
- 1 ship → 1.0 units/turn
- 10 ships → 1.0 + 5.0 × (1/3)^1.5 ≈ 1.96
- 50 ships → 1.0 + 5.0 × (1.699/3)^1.5 ≈ 3.57
- 100 ships → ~4.23
- 500 ships → ~5.05
- 1000 ships → 6.0 (max)

**Implication for Gap 5**: `garrison + 1 = 1 ship` travels at 1.0 units/turn. Setting `MIN_FAST_FLEET = 10` gives 1.96 units/turn — roughly 2× the speed. For a 15-unit trip, this saves ~7 turns of travel.

## R-5: Safety Threshold Calibration

**Decision**: `safety_threshold = planet.production × 10`. Confirmed from clarification session.

**Rationale**: A planet producing P ships/turn recovers `P × 10` ships in 10 turns. Holding that as a floor means the planet can survive a moderately-sized attack (10 turns of production worth) while still allowing surplus to be dispatched. For production=1, threshold=10; for production=5, threshold=50.

**Edge case**: A high-production planet (P=5) with only 45 ships will never send reinforcements (threshold=50). This is conservative but correct — a stripped production-5 planet is a severe strategic loss.

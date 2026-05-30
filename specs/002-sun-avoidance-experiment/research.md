# Research: Sun Avoidance Experiment

**Phase**: 0 | **Feature**: 002-sun-avoidance-experiment | **Date**: 2026-05-29

## Finding 1: Sun Position and Radius Are Hardcoded Constants

**Decision**: The agent must hard-code `CENTER = 50.0` and `SUN_RADIUS = 10.0` — these are not in the observation.

**Rationale**: The game engine in `orbit_wars.py` defines `BOARD_SIZE = 100.0`, `CENTER = BOARD_SIZE / 2.0 = 50.0`, and `SUN_RADIUS = 10.0` as module-level constants. The observation passed to agents contains only: `player`, `planets`, `fleets`, `step`, `angular_velocity`, `comets`, `comet_planet_ids`, `initial_planets`, `next_fleet_id`, `remainingOverageTime`. No sun-related field is exposed.

**Alternatives considered**: Dynamically reading configuration — not possible since `configuration.seed` is scrubbed; no `sunRadius` key exists in configuration.

---

## Finding 2: Collision Check is Point-to-Segment Distance

**Decision**: Use the same `point_to_segment_distance` formula that the engine uses to pre-screen fleet paths.

**Rationale**: The engine destroys a fleet on each tick if:
```
point_to_segment_distance((CENTER, CENTER), old_pos, new_pos) < SUN_RADIUS
```
where `old_pos` and `new_pos` are the fleet's position at the start and end of one tick. Fleets travel in a straight line at speed `1.0 + (max_speed - 1.0) * (log(ships) / log(1000))^1.5` (capped at `max_speed = 6`). A fleet dispatched from planet A to planet B travels in the angle `atan2(B.y - A.y, B.x - A.x)` until it hits the destination planet.

**Practical simplification**: For path pre-screening at dispatch time, we can check whether the **line segment from source to target** passes within `SUN_RADIUS` of `CENTER`. This is a conservative check — it catches all sun-crossing paths without needing to simulate per-tick positions. The formula:

```python
def segment_min_dist_to_sun(ax, ay, bx, by):
    """Min distance from the line segment A->B to the sun center (50, 50)."""
    px, py = 50.0, 50.0  # CENTER
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return math.hypot(ax - px, ay - py)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)
```

**Alternatives considered**: Per-tick simulation — accurate but complex and slow; not needed since the straight-line path check is equivalent for dispatch decisions.

---

## Finding 3: Avoidance Strategy — Skip or Detour

**Decision**: For the initial experiment, **skip sun-crossing targets** rather than computing a detour route, then fall back to the best non-crossing candidate.

**Rationale**: Computing a detour arc (e.g., tangent waypoint) requires a two-segment path, which the engine does not natively support in a single fleet dispatch (an agent returns `[from_id, angle, ships]` — one angle, one source planet). True arc routing would require splitting a fleet into sequential dispatches across intermediate waypoints, which adds significant complexity and may not be necessary if enough safe targets exist.

Skipping approach: re-rank candidates by production/distance score, ignoring any where `segment_min_dist_to_sun < SUN_RADIUS + SAFETY_MARGIN`. This is simpler, fully self-contained, and testable independently.

**Safety margin**: Add a buffer of `2.0` units (i.e., check `< SUN_RADIUS + 2.0`) to account for the fact that planets orbit — their positions shift each turn, so a path that barely clears the sun now may cross it next tick.

**Alternatives considered**:
- True arc routing via tangent waypoint: accurate but requires multi-step dispatch not supported in single-turn agent actions.
- Skip without fallback: agent would do nothing if all targets cross the sun — rejected; a lower-scoring safe target is better than no action.

---

## Finding 4: Evaluation Pairing Plan

**Decision**: Run two separate eval sessions — `agent_v3.py vs main.py` (10 games, seeds 0–9) and `agent_v3.py vs agent_v2.py` (10 games, seeds 0–9) — using the existing `eval.py` harness unchanged.

**Rationale**: `eval.py` already accepts `--agent0` and `--agent1` flags. No modifications needed. Running with `--verbose` on 3 games can also show whether the new agent bypasses targets it previously would have attacked (observable strategy difference).

---

## Finding 5: Agent Naming Convention

**Decision**: Name the new agent `agent_v3.py`.

**Rationale**: The project uses sequential versioning (baseline = `main.py`, production-weighted = `agent_v2.py`). Sun-aware production-weighted = `agent_v3.py`.

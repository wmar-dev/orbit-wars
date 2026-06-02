# Implementation Plan: Fix Fleet Targeting When Both Source and Target Are Moving

**Branch**: `017-fix-moving-planet-targeting` | **Date**: 2026-06-02 | **Spec**: [spec.md](spec.md)

## Summary

Fleet targeting fails when both source and target planets are orbiting for two reasons:
(A) the orbit lead uses the source's planet center as the launch origin, but the game engine launches the fleet from `planet.center + direction × (radius + 0.1)`, causing the fleet to arrive early and miss small targets; and (B) the path safety check uses current positions of intermediate orbiting planets, causing valid dispatch opportunities to be blocked when those planets happen to be in the current line-of-sight. The fix creates a new agent version (`agent_v57.py`) that corrects both issues.

## Technical Context

**Language/Version**: Python 3.14 (local .venv), compatible with Kaggle sandbox (3.10+)

**Primary Dependencies**: `math` (stdlib), `kaggle_environments` (Planet namedtuple)

**Storage**: N/A — stateless per-turn agent

**Testing**: `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 50 --jobs 8`

**Target Platform**: Kaggle Orbit Wars sandbox (single `.py` file, Option A submission)

**Performance Goals**: ≥ 55% win rate vs agent_v56 at 50 games; ≤ 1s per turn decision (current agent is ~10ms)

**Constraints**: Single-file submission (Option A). All changes inlined. No new imports beyond `math` and `kaggle_environments`.

**Scale/Scope**: Two targeted changes to `_converged_orbit_lead` and `_path_safe`.

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. RL First | ✅ Pass | Heuristic bug fix; acceptable as baseline improvement. No RL substitution. |
| II. Fair Play | ✅ Pass | No rule exploits. |
| III. Manual Submissions | ✅ Pass | Submit manually after eval confirms improvement. |
| IV. Documentation | ✅ Pass | Hypothesis, change, result, conclusion documented here. |
| V. Local Self-Play ≥ 20 games | ✅ Pass | Plan requires 50-game eval before submission. |
| VI. Submission Package | ✅ Pass | Single-file agent. |
| VII. 95% Confidence Gate | ✅ Pass | Requires ≥ 55% at 50 games before submission. |

## Project Structure

### Documentation (this feature)

```text
specs/017-fix-moving-planet-targeting/
├── plan.md              # This file
├── research.md          # Phase 0 output — game engine analysis
├── spec.md              # Feature spec
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (not yet created)
```

### Source Code (repository root)

```text
agent_v56.py         # Current best agent (baseline)
agent_v57.py         # New agent with both fixes (created by this feature)
eval.py              # Self-play evaluator
```

---

## Phase 0: Research (Complete)

See [research.md](research.md) for full findings.

**Key decisions:**

| Decision | Rationale |
|----------|-----------|
| Fix launch offset in orbit lead (Fix A) | Game engine launches fleets `radius + 0.1` ahead of planet center; orbit lead uses planet center — causes measurable early-arrival error for small planets |
| Predict intermediate planet positions in path safety (Fix B) | Orbiting intermediates currently in path may have moved; this blocks valid attacks unique to both-orbiting scenarios |
| One additional orbit lead correction pass for source radius | Self-consistent with target prediction; negligible cost |
| 50-game eval threshold | Sufficient sample size per constitution Principle V |

---

## Phase 1: Design & Implementation

### Change 1 — Fix A: Source Radius Correction in Orbit Lead

**Where**: `_converged_orbit_lead` call sites, or a new wrapper function.

**Mechanism**: After computing the initial orbit lead from `mine.center`, derive the actual launch position `(lx, ly) = mine.center + unit_vec * (mine.radius + 0.1)`. Re-run orbit lead from `(lx, ly)` to get a corrected aim point. Use the corrected aim point for the fleet angle.

**Implementation pattern**:
```python
def _launch_corrected_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed):
    # Initial estimate from planet center
    ax, ay = _converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed)
    # Correction: actual launch is planet.radius + 0.1 ahead of center
    dist = math.hypot(ax - mine.x, ay - mine.y)
    if dist < 1e-6:
        return ax, ay
    ux, uy = (ax - mine.x) / dist, (ay - mine.y) / dist
    lx = mine.x + ux * (mine.radius + 0.1)
    ly = mine.y + uy * (mine.radius + 0.1)
    mine_launch = type('M', (), {'x': lx, 'y': ly})()
    return _converged_orbit_lead(t, mine_launch, initial_planets_map, angular_velocity, speed)
```

Apply this wrapper everywhere `_converged_orbit_lead` is called with `mine` as source — in the main attack loop, evacuation loop, and `_enemy_fleet_size`. Do NOT apply to `_enemy_fleet_size`'s internal recompute (which already has a separate mine_fake with explicit coordinates).

**Angle computation**: The fleet angle must be computed from the LAUNCH POSITION, not the planet center:
```python
# Before fix:
angle = math.atan2(by - mine.y, bx - mine.x)
# After fix:
# ux, uy already computed above; angle = atan2(ay - mine.y, ax - mine.x) ≈ atan2(uy, ux)
# But bx, by is the new aim — compute angle from planet center is fine since launch is on the same line
angle = math.atan2(by - mine.y, bx - mine.x)  # unchanged: launch is collinear with center and aim
```

Note: the angle is computed from `mine.center` to the aim point. The launch position is collinear with center and aim (it's in the same direction), so the angle is identical. The correction only affects the TRAVEL TIME used in the orbit lead, not the dispatch angle. Angle computation is unchanged.

### Change 2 — Fix B: Predicted Intermediate Planet Positions in Path Safety

**Where**: `_path_safe` function and its call sites.

**Mechanism**: For orbiting intermediate planets, predict their position at the midpoint of the fleet's estimated travel time instead of using their current position. For static planets, use the current position (unchanged behavior).

**New signature**:
```python
def _path_safe(ox, oy, tx, ty, all_planets=None, target_id=None, source_id=None,
               initial_planets_map=None, angular_velocity=0.0, travel_turns=0.0):
```

**Implementation**:
```python
if all_planets:
    mid_travel = travel_turns / 2.0
    for p in all_planets:
        if p.id == target_id or p.id == source_id:
            continue
        # Use predicted position for orbiting planets, current for static
        if initial_planets_map and angular_velocity > 0 and mid_travel > 0:
            px, py = _predict_planet_pos(p, initial_planets_map, angular_velocity, mid_travel)
        else:
            px, py = p.x, p.y
        clearance = p.radius + PLANET_MARGIN
        if _segment_dist_to_point(ox, oy, tx, ty, px, py) < clearance:
            return False
```

**Call site update**: Pass `initial_planets_map`, `angular_velocity`, and `travel_turns` from the computed orbit lead wherever `_path_safe` is called.

### Change 3 — Agent Version Increment

- Copy `agent_v56.py` to `agent_v57.py`
- Apply Fix A and Fix B
- Update docstring with hypothesis, changes, and result placeholder
- Update `main.py` to reference agent_v57

### Eval Plan

| Eval | Command | Pass threshold |
|------|---------|----------------|
| Screen (50 games) | `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 50 --jobs 8` | ≥ 45% (no regression) |
| Full eval (200 games) | `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 200 --jobs 8` | ≥ 55% |
| Static sanity | `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 50 --jobs 8 --seed static_only` | 48–52% (no regression on static-only maps, if eval supports seed filtering) |

If 50-game screen < 45%: diagnose further before proceeding. If 200-game result < 55%: do not submit but document findings.

**Testing**: `uv run python eval.py --agent0 agent_v57.py --agent1 agent_v56.py --games 50 --jobs 8`

**Performance Goals**: Win rate ≥ 55% vs agent_v56 at 95% statistical confidence

---

## Complexity Tracking

No constitution violations. Both changes are bug fixes within the existing single-file agent structure.

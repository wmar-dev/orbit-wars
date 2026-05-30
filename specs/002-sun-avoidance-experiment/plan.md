# Implementation Plan: Sun Avoidance Experiment

**Branch**: `002-sun-avoidance-experiment` | **Date**: 2026-05-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-sun-avoidance-experiment/spec.md`

## Summary

Implement `agent_v3.py` — a sun-safe variant of `agent_v2.py` — by adding a single path-safety
filter before target selection: any candidate planet whose straight-line dispatch path from
source comes within `SUN_RADIUS + SAFETY_MARGIN` of the sun center is excluded. Then run a
structured 2-vs-2 evaluation (`agent_v3 vs main.py`, `agent_v3 vs agent_v2`) using the
existing `eval.py` harness and record results in the experiment log.

## Technical Context

**Language/Version**: Python 3.14 (project constraint in pyproject.toml)

**Primary Dependencies**: `kaggle-environments ≥1.28.0` (already installed); `math` stdlib only

**Storage**: N/A — no persistence; eval results printed to stdout only

**Testing**: Manual — `uv run python eval.py` for head-to-head evaluation

**Target Platform**: Local macOS/Linux dev machine (same env as existing Makefile workflows)

**Project Type**: CLI / script — single-file agent at project root

**Performance Goals**: Turn decision in <1 second; 10-game eval in <30 seconds per pairing

**Constraints**: Pure Python, no external models or network calls; agent file must be
self-contained at project root for Kaggle submission compatibility

**Scale/Scope**: 2 eval pairings × 10 games each; single agent implementation

**Key constants (hardcoded — not in observation)**:

- `CENTER = 50.0` (sun x and y)
- `SUN_RADIUS = 10.0` (engine destruction threshold)
- `SAFETY_MARGIN = 2.0` (buffer for orbital planet drift)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Rationale |
| --------- | ------ | --------- |
| I. RL First | ✅ Pass | Rule-based heuristic is explicitly permitted as baseline / opponent seed |
| II. Fair Play | ✅ Pass | No engine bug exploitation; uses same geometry the engine uses |
| III. Manual Submissions Only | ✅ Pass | No automation; evaluation is local only per spec |
| IV. Experiment Documentation | ✅ Pass (conditional) | Experiment log at `experiments/2026-05-29-sun-avoidance.md` MUST be written before any Kaggle submission |
| V. Local Self-Play Eval | ✅ Pass | Spec mandates 10-game eval vs both baseline and agent_v2 |

**Gate result**: PASS. No violations. Experiment log creation is a required deliverable.

## Project Structure

### Documentation (this feature)

```text
specs/002-sun-avoidance-experiment/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── data-model.md        ← Phase 1 output
├── quickstart.md        ← Phase 1 output
├── contracts/
│   └── agent-interface.md  ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
orbit-wars/
├── main.py              # baseline — do not modify
├── agent_v2.py          # production-weighted — do not modify
├── agent_v3.py          # NEW: sun-aware production-weighted agent
├── eval.py              # existing harness — no changes needed
├── experiments/
│   └── 2026-05-29-sun-avoidance.md   # NEW: required experiment log
└── Makefile             # may extend with make eval3 convenience target
```

**Structure Decision**: Flat root layout, matching existing convention. `agent_v3.py` at root
for Kaggle submission compatibility.

## Phase 0: Research Findings

See [research.md](research.md) for full findings. Key decisions:

1. **Sun constants hardcoded**: `CENTER = 50.0`, `SUN_RADIUS = 10.0` — not in observation.
2. **Collision check**: Use `point_to_segment_distance` formula — same as engine uses per tick.
3. **Avoidance strategy**: Skip sun-crossing targets (no arc routing needed for v1).
4. **Safety margin**: `SUN_RADIUS + 2.0 = 12.0` to buffer against orbital planet drift.
5. **Agent name**: `agent_v3.py`.

## Phase 1: Design

See [data-model.md](data-model.md) for entities and decision flow.
See [contracts/agent-interface.md](contracts/agent-interface.md) for agent I/O contract.
See [quickstart.md](quickstart.md) for eval commands.

### Core algorithm delta from agent_v2

```python
# New helper (added to agent_v3.py):
def _segment_dist_to_sun(ax, ay, bx, by):
    px, py = 50.0, 50.0
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return math.hypot(ax - px, ay - py)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)

SUN_EXCLUSION = SUN_RADIUS + SAFETY_MARGIN  # 12.0

# In target filtering loop (replaces agent_v2's candidate selection):
candidates = [
    t for t in targets
    if math.hypot(t.x - mine.x, t.y - mine.y) <= max_range
    and _segment_dist_to_sun(mine.x, mine.y, t.x, t.y) >= SUN_EXCLUSION
]
# Fallback: all sun-safe targets if none in range
if not candidates:
    candidates = [
        t for t in targets
        if _segment_dist_to_sun(mine.x, mine.y, t.x, t.y) >= SUN_EXCLUSION
    ]
# If still none (all targets sun-crossing): skip this planet
if not candidates:
    continue
```

## Complexity Tracking

No constitution violations requiring justification.

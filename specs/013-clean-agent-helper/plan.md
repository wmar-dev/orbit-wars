# Implementation Plan: Clean Agent with Helper Module

**Branch**: `013-clean-agent-helper` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-clean-agent-helper/spec.md`

## Summary

Create `helper.py` — a pure-function module containing all deterministic game-mechanics calculations from the agent_v38/v40 lineage — and `agent_v41.py` — a clean reimplementation that imports from `helper.py` and contains only parsing and decision logic. The result is a ≤350 LOC agent file and a standalone helper library that human agent authors can import directly. Evaluate agent_v41 vs agent_v38 (≥50% target) and agent_v40 (≥45% target) across 50 games each with seed 0.

## Technical Context

**Language/Version**: Python 3.14 (repo requirement per CLAUDE.md)

**Primary Dependencies**: `kaggle-environments>=1.28.0` (already installed); `math` stdlib only in agent and helper files

**Storage**: Flat files at repo root (`helper.py`, `agent_v41.py`); experiment record at `experiments/013-clean-agent-helper.md`

**Testing**: `uv run python eval.py --agent0 agent_v41.py --agent1 agent_v38.py --games 50 --seed 0` and `uv run python eval.py --agent0 agent_v41.py --agent1 agent_v40.py --games 50 --seed 0`; `make test` smoke test vs random

**Target Platform**: Local macOS development (evaluation), Kaggle submission sandbox (inference — Principle VI Option B multi-file package)

**Project Type**: Competitive game agent — rule-based heuristics, no training infrastructure

**Performance Goals**: ≥50% win rate vs agent_v38 (50 games, seed 0); ≥45% win rate vs agent_v40 (50 games, seed 0); turn time <1 second (pure math/stdlib)

**Constraints**: `agent_v41.py` MUST import from `helper.py` (not re-implement inline). Both files submitted together as a Kaggle multi-file package (Principle VI Option B). No torch or ML inference at runtime. All logic pure Python + stdlib + kaggle_environments.

**Scale/Scope**: `helper.py` ~150 LOC; `agent_v41.py` ≤350 LOC. Single experiment record for all eval runs.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Reinforcement Learning First | ✅ Exempt | Constitution permits heuristic baseline agents. This feature improves the heuristic baseline; RL path (spec 011) remains the primary improvement track. |
| II. Fair Play & Rules Compliance | ✅ Pass | No engine modifications. actTimeout <1s enforced (pure math/stdlib). |
| III. Manual Submissions Only | ✅ Pass | Kaggle submission is out of scope for this feature; only local eval is performed. |
| IV. Experiment & Improvement Documentation | ✅ Pass | `experiments/013-clean-agent-helper.md` required with hypothesis, change, self-play result, and conclusion before any future submission. |
| V. Local Self-Play as Primary Evaluation Loop | ✅ Pass | 50-game eval vs agent_v38 and agent_v40 with seed 0 before promotion decision. |
| VI. Submission Package Completeness | ✅ Pass | agent_v41.py + helper.py submitted together as Option B multi-file package. Pre-submission check command documents both files. |

**Result**: All gates pass. Proceeding to implementation.

---

## Project Structure

### Documentation (this feature)

```text
specs/013-clean-agent-helper/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # Phase 1 output (helper.py public API)
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
helper.py                # Pure-function game-mechanics library (new)
agent_v41.py             # Clean agent importing from helper.py (new)

experiments/
└── 013-clean-agent-helper.md   # Eval results (new)
```

**Structure Decision**: Flat repo root. `helper.py` and `agent_v41.py` at root alongside all other agent files. Matches existing convention. No new directories needed.

---

## Phase 0: Research

### Decision Log

**D-001: Which mechanics from agent_v40 are proven vs experimental?**

- Decision: Retain all mechanics that survived evaluation (are present in agent_v38 and agent_v40 final form). Remove all variant flags and experimental code paths.
- Proven mechanics to retain:
  - `_segment_dist_to_point` / `_segment_dist_to_sun` / `_ray_exits_board` — geometry primitives (v9)
  - `_path_safe` — full-ray sun check + intermediate planet obstruction + OOB guard (v9/v10)
  - `fleet_speed` — fleet speed formula from CONTEST.md (v7)
  - `_predict_planet_pos` — orbital position prediction (v4)
  - `_converged_orbit_lead` — iterative convergence for orbit-lead targeting (v32 Fix 2)
  - `_build_comet_path_lookup` / `_comet_predicted_pos` / `_comet_two_pass` — comet intercept (v8/v32)
  - `_roi` — production-squared ROI scoring (Candidate R, v33)
  - `_reward_estimate` — reward-blend scoring helper (Candidate S, v31)
  - `_angle_diff` — angle difference utility (v38 Candidate U)
  - `_planet_value` — production-weighted value score (v40)
  - `_enemy_incoming` — enemy fleet race-condition detection (v40)
  - `_banking_mode` — ship-banking phase gate (v40, Variant B locked)
  - `_predict_target` — unified orbit-lead / comet two-pass dispatch (v40)
- Mechanics removed (experimental/failed):
  - `BANKING_VARIANT` / `FALLBACK_VARIANT` flags — Variant B + C locked in; flags removed
  - `assigned_primary` / `assigned_secondary` sets — unused dead code in v40
  - `high_prod_neutrals` / `high_prod_enemies` — populated but not used in final v40 attack loop
  - Duplicate constants (RANGE_FACTOR=2.0 — unused since Candidate Q removed range cap)
- Rationale: Clean slate from v40's proven core; dead code and variant flags are pure noise

**D-002: What should `helper.py` export?**

- Decision: Export all functions listed in FR-001 as top-level public functions. Rename private `_` prefix to public names. Add `__all__` for explicit API surface.
- Rename map:
  - `_segment_dist_to_point` → `segment_dist_to_point`
  - `_segment_dist_to_sun` → `segment_dist_to_sun`
  - `_ray_exits_board` → `ray_exits_board`
  - `_path_safe` → `path_safe`
  - `fleet_speed` → `fleet_speed` (already public)
  - `_predict_planet_pos` → `predict_planet_pos`
  - `_converged_orbit_lead` → `converged_orbit_lead`
  - `_build_comet_path_lookup` → `build_comet_path_lookup`
  - `_comet_predicted_pos` → `comet_predicted_pos`
  - `_comet_two_pass` → `comet_two_pass`
  - `_roi` → `roi`
  - `_reward_estimate` → `reward_estimate`
  - `_angle_diff` → `angle_diff`
  - `_planet_value` → `planet_value`
  - `_enemy_incoming` → `enemy_incoming`
  - `_banking_mode` → `banking_mode`
  - `_predict_target` → `predict_target`
  - `math.atan2(dy, dx)` inline → `angle_to(x1, y1, x2, y2)` convenience wrapper
- Rationale: `_` prefix signals "private implementation detail" — the whole point of `helper.py` is to be a public API for human authors. All functions should be first-class accessible.

**D-003: Should `helper.py` import `Planet` from kaggle_environments?**

- Decision: No. `helper.py` works with duck-typed objects (anything with `.x`, `.y`, `.id`, `.ships`, `.production`, `.owner`, `.radius` attributes). The `Planet` namedtuple import stays in `agent_v41.py` for observation parsing. This makes `helper.py` importable without `kaggle_environments` installed (SC-001).
- Rationale: Enables `python -c "import helper"` smoke test without game environment; supports unit testing of helpers in isolation.

**D-004: Should constants (GARRISON_FLOOR_FACTOR, ANGLE_EPSILON, etc.) live in `helper.py`?**

- Decision: Yes — all tunable constants go in `helper.py`. They are part of the public interface that human authors may want to override. `agent_v41.py` imports them from `helper.py` and does not redeclare them.
- Rationale: Centralizes all "knobs" in one place. A human writing a custom agent can do `from helper import GARRISON_FLOOR_FACTOR` and use it directly.

**D-005: How should `agent_v41.py` handle the obs parsing (dict vs namedtuple)?**

- Decision: Keep the `obs.get(...) if isinstance(obs, dict) else obs.field` pattern for observation parsing at the top of `agent()`. This is boilerplate but correct; do not add a helper for it since it's a one-time parse block, not a reusable computation.
- Rationale: Adding a helper for obs parsing adds indirection without clarity gain. The pattern is already well understood in this codebase.

**D-006: What is the confirmed best variant configuration for banking?**

- Decision: BANKING_VARIANT="B" (ceiling = my_prod × 25 turns), FALLBACK_VARIANT="C" (hybrid). These are locked in per the agent_v40 promotion decision recorded in the README. No further variant evaluation is needed for agent_v41.
- Rationale: agent_v40 was promoted to best agent on this configuration; agent_v41 inherits it.

---

## Phase 1: Design

### Data Model

See [data-model.md](data-model.md).

### Contracts

See [contracts/helper-api.md](contracts/helper-api.md).

---

## Implementation Notes

### `helper.py` module layout

```text
helper.py
  Constants block           # All tunable constants (GARRISON_FLOOR_FACTOR, SUN_EXCLUSION, etc.)
  __all__ list              # Explicit public API
  Geometry primitives       # segment_dist_to_point, segment_dist_to_sun, ray_exits_board
  Path safety               # path_safe
  Fleet mechanics           # fleet_speed, angle_to
  Orbital prediction        # predict_planet_pos, converged_orbit_lead
  Comet mechanics           # build_comet_path_lookup, comet_predicted_pos, comet_two_pass
  Scoring functions         # roi, reward_estimate, planet_value, enemy_incoming
  Strategy helpers          # angle_diff, banking_mode, predict_target
```

### `agent_v41.py` module layout

```text
agent_v41.py
  Module docstring          # Summary of what changed from v40
  Imports                   # math, Planet, and all from helper
  agent(obs) function
    Observation parsing     # ~15 lines: extract player, planets, fleets, etc.
    State derivation        # my_planets, enemy_planets, targets, initial_planets_map
    Threat detection        # build threat dict from raw_fleets
    Comet setup             # build_comet_path_lookup, departing/evacuate sets
    Early exits             # if not my_planets or not targets
    Banking check           # banking_mode(...)
    Evacuation loop         # for mine in evacuate_this_turn
    Sender assignment       # best_sender dict (dist/surplus scoring)
    Attack loop             # per-planet candidate targeting + blended ROI
    Return moves
```

### Key simplifications vs agent_v40

1. **Dead code removal**: `assigned_primary`, `assigned_secondary`, `high_prod_neutrals`, `high_prod_enemies`, `neutral_targets`, `enemy_targets` (duplicating `targets`) all removed.
2. **Variant flags removed**: `BANKING_VARIANT`, `FALLBACK_VARIANT` — replaced with locked-in values.
3. **Duplicate docstring lines removed**: agent_v40 has duplicated "Base logic inherited" lines in its module docstring.
4. **`predict_target` helper**: The orbit-lead / comet dispatch logic duplicated in evacuation loop and attack loop in agent_v38/v40 is unified into `helper.predict_target`.
5. **`angle_to` convenience**: Replaces all `math.atan2(y2-y1, x2-x1)` inline calls with a named function.

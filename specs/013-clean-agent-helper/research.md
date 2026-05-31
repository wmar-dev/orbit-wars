# Research: Clean Agent with Helper Module

**Feature**: 013-clean-agent-helper | **Date**: 2026-05-31

## Summary

All research questions are resolved from existing codebase analysis. No external research is needed — this feature is a refactoring of proven mechanics with no new game strategies.

## Findings

### F-001: Function inventory across agent_v38 and agent_v40

All functions in agent_v38 and agent_v40 were audited. The complete list of proven functions is documented in plan.md D-001. No functions in agent_v38/v40 are missing from the helper API design.

Dead code confirmed in agent_v40:
- `assigned_primary` / `assigned_secondary` sets — populated but never used to gate any logic
- `high_prod_neutrals` / `high_prod_enemies` — populated but never referenced in the attack loop
- `neutral_targets` / `enemy_targets` — redundant re-filters of `targets` with `p.owner == -1` / `p.owner >= 0`
- `FALLBACK_VARIANT` — the `"C"` branch is never reached (no code path branches on it in the final attack loop)
- `RANGE_FACTOR = 2.0` — unused since Candidate Q (no range cap) was adopted in v28

### F-002: `helper.py` importability without kaggle_environments

Confirmed: `kaggle_environments` is only needed for `Planet(*raw)` namedtuple construction, which is observation parsing. All helper functions operate on duck-typed objects with `.x`, `.y`, `.id`, `.ships`, `.production`, `.owner`, `.radius`. Removing the `Planet` import from `helper.py` makes it independently importable.

### F-003: Eval harness interface

`eval.py` accepts `--agent0`, `--agent1`, `--games`, `--seed` flags and loads agents via `importlib.util.spec_from_file_location`. Multi-file agents work if `helper.py` is in the same directory (Python adds the script's directory to `sys.path`). No changes to `eval.py` needed.

### F-004: Proven constant values

All constants confirmed from experiments/:
- `GARRISON_FLOOR_FACTOR = 3` — Candidate O (v26, 55% vs v20)
- `REWARD_ALPHA = 0.1` — Candidate S (v31, 61% vs v30)
- `ANGLE_EPSILON = 0.1` — Candidate U (v36/v38, 86% vs v33)
- `RACE_EPSILON = 0.2` — v40 (wider than ANGLE_EPSILON for orbit-lead prediction error)
- `EVACUATE_THRESHOLD = 3` — v8/v32 (comet evac with ≤3 turns remaining)
- `ORBIT_LEAD_EPS = 0.1`, `ORBIT_LEAD_MAX_ITER = 10` — v32 convergence (Fix 2)
- `BANK_PROD_THRESHOLD = 1.3`, `BANK_TURNS_FACTOR = 25` — v40 Variant B banking
- `PROD_WEIGHT = 2.0`, `DIST_WEIGHT = 1.0` — v40 planet value scoring
- `SUN_EXCLUSION = 12.0` (SUN_RADIUS=10 + SAFETY_MARGIN=2) — v9 sun avoidance

### F-005: Line count targets

- agent_v40.py: 477 lines
- agent_v38.py: 355 lines (no dead code from v40 additions)
- Expected agent_v41.py with helper extraction: ~200–280 lines
- Expected helper.py: ~150–200 lines
- SC-004 target (≤350 for agent_v41.py) is achievable with comfortable margin

## Decisions Made

All decisions documented in plan.md D-001 through D-006. No NEEDS CLARIFICATION items remain.

# Implementation Plan: Comet Evacuation Fix, Fleet Targeting Accuracy, and Agent Improvement Experiments

**Branch**: `009-fix-comet-fleet-targeting` | **Date**: 2026-05-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-fix-comet-fleet-targeting/spec.md`

## Summary

Fix two confirmed behavioral bugs in agent_v31 (comet non-evacuation, orbit-lead targeting misses), save the corrected version as agent_v32, then run a structured experiment round that retests previously-failed candidates (I, J, K, L, P, R) against the fixed baseline. Evaluation uses both win-rate (primary, 55% threshold) and mid-game reward signal (secondary, via the existing `reward_signal.py` + `--reward-log` flag). Only the best combined agent (v32 + best passing candidate, or v32 alone) is submitted to Kaggle.

## Technical Context

**Language/Version**: Python 3.14 (project venv at `.venv/`)

**Primary Dependencies**: `kaggle_environments` (orbit_wars engine, Planet/Fleet namedtuples), `eval.py` (evaluation harness with `--reward-log` support), `reward_signal.py` (per-turn reward computation, feature-008 output)

**Storage**: `.jsonl` reward logs per candidate experiment; `experiments/` directory for experiment records per constitution

**Testing**: `eval.py --games 50` (win-rate primary); `eval.py --reward-log` (reward signal secondary); manual game trace inspection

**Target Platform**: Local macOS/Linux (flat repo root)

**Project Type**: Research bot / game agent (flat repo root layout, no package structure)

**Performance Goals**: Convergence loop overhead negligible (<1ms/fleet/turn); overall eval wall-clock unchanged

**Constraints**: No external ML libraries; pure Python math; all other agent logic (ROI, garrison floor, sun avoidance, single-sender) is unchanged

**Scale/Scope**: 2-player; 50-game eval batches per candidate; reward log ~1–5 MB per run

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. RL First | ✅ Pass | Bug fixes and iterative convergence improve the heuristic baseline; reward-signal-augmented evaluation is a step toward RL-guided selection. Full learned policy deferred. |
| II. Fair Play | ✅ Pass | All fixes use only documented observation fields (`paths`, `path_index`, `angular_velocity`, `initial_planets`) per CONTEST.md. No engine exploits. |
| III. Manual Submissions | ✅ Pass | One deliberate submission after all experiments conclude. No automated pipeline. |
| IV. Experiment Documentation | ✅ Pass | Each candidate run produces an experiment record in `experiments/` before the pass/fail verdict. |
| V. Local Self-Play | ✅ Pass | Every candidate evaluated over 50 games (≥20 minimum per constitution). Submission only after local self-play confirms improvement. |

## Project Structure

### Documentation (this feature)

```text
specs/009-fix-comet-fleet-targeting/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── eval-cli.md      # Updated CLI contract for reward-log usage pattern
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
agent_v32.py             # Fixed baseline: comet evacuation + converged orbit-lead
agent_v33.py             # Combined agent (v32 + best passing candidate) — created only if candidate passes
experiments/
├── 009-candidate-I-retest.md
├── 009-candidate-J-retest.md
├── 009-candidate-K-retest.md
├── 009-candidate-L-retest.md
├── 009-candidate-P-retest.md
└── 009-candidate-R-retest.md
```

## Phase 0: Research

*See [research.md](research.md) for full findings.*

### Key Decisions

**R-001 — Comet remaining-life field**
- Decision: compute `remaining_turns = max(0, len(path) - path_index)` from the two documented fields
- Rationale: `remaining_steps` is not in the CONTEST.md observation reference and is likely absent or always 0. `paths` and `path_index` are documented and reliable.
- Alternative rejected: trusting `remaining_steps` — caused the original bug

**R-002 — Orbit-lead convergence algorithm**
- Decision: fixed-point iteration with early exit on `delta < 0.1` units, capped at 10 iterations
- Rationale: The Newton-like update `theta_{n+1} = f(theta_n)` is a contraction mapping for the intercept problem when the target speed (tangential) is much less than fleet speed. Convergence is guaranteed in practice; the cap handles degenerate edge cases.
- Alternative rejected: bisection / binary search on travel time — correct but 3× slower for no accuracy gain at 10-iteration cap

**R-003 — Comet two-pass intercept**
- Decision: two Newton passes (same as the new converged_orbit_lead loop, but capped at 2 for comets since their speed is constant and the path is piecewise linear)
- Rationale: Comets move at a fixed speed (4.0 units/turn per CONTEST.md) on a pre-computed path. One extra pass substantially closes the targeting error; further passes give diminishing returns and the path lookup uses integer indexing anyway.
- Alternative rejected: full convergence loop — integer path indexing creates a quantization floor that makes further iterations wasteful

**R-004 — Evacuation target pool**
- Decision: pool = all safe planets (owned ∪ non-owned). Owned planets scored by `production / (dist + ε)`; non-owned by ROI. Best overall score wins.
- Rationale: Owned planets guarantee ship preservation; non-owned may yield higher value. A unified scored pool lets the agent pick optimally without hardcoded priority.
- Alternative rejected: owned-only fallback after no enemy path — two-tier logic is harder to test and may still miss the globally best option

**R-005 — Reward signal in candidate evaluation**
- Decision: run `eval.py --reward-log experiments/009-candidate-X.jsonl` for every candidate. Report both win-rate (primary) and mean per-turn reward delta vs. v32 (secondary). Secondary signal is informational only — it does not override the 55% pass/fail gate.
- Rationale: Mid-game reward delta catches candidates that improve decision quality but whose gains don't yet accumulate to a win-rate difference at N=50. Provides forward-looking data even for borderline failures.
- Alternative rejected: reward signal as a co-equal gate — too noisy at N=50 to be a reliable gate; keeps win-rate as the single authoritative criterion

**R-006 — Previously-failed candidate re-evaluation order**
- Decision: test in order P → J → K → R → L → I (highest-upside-from-bug-fix first)
- Rationale: Candidate P (3-iteration orbit lead) failed because of the targeting bug it was attempting to improve; it is the most likely to flip. J and K were statistical ties vs. v20 (50%, 20 draws) and may distinguish themselves on the fixed base. L and I had larger gaps and are tested last.

## Phase 1: Design & Contracts

### Functional Changes

#### 1. `_comet_remaining_turns(pid, comet_path_lookup) → int`

New helper that reads from the comet path lookup built in `_build_comet_path_lookup`:

```
remaining = max(0, len(path) - path_index)
```

Replaces the `remaining_steps` field read in `departing_this_turn` / `evacuate_next_turn` detection.

Evacuation threshold: `EVACUATE_THRESHOLD = 3`. Triggers when `remaining <= EVACUATE_THRESHOLD`.

#### 2. `_converged_orbit_lead(t, mine, initial_planets_map, angular_velocity, speed, max_iter=10, eps=0.1) → (float, float)`

Replaces `_refined_orbit_lead`. Fixed-point loop:

```
x, y = t.x, t.y
for _ in range(max_iter):
    travel = hypot(x - mine.x, y - mine.y) / speed
    nx, ny = _predict_planet_pos(t, initial_planets_map, angular_velocity, travel)
    if hypot(nx - x, ny - y) < eps:
        return nx, ny
    x, y = nx, ny
return x, y
```

#### 3. `_comet_two_pass(comet_planet, mine, comet_path_lookup, speed) → (float, float, bool)`

Replaces single-step comet position lookup in the targeting block:

```
# Pass 1
t0 = hypot(comet.x - mine.x, comet.y - mine.y) / speed
x1, y1, valid = _comet_predicted_pos(comet, path_lookup, t0)
if not valid: return comet.x, comet.y, False
# Pass 2
t1 = hypot(x1 - mine.x, y1 - mine.y) / speed
x2, y2, valid2 = _comet_predicted_pos(comet, path_lookup, t1)
return (x2, y2, True) if valid2 else (x1, y1, True)
```

#### 4. Evacuation target selection

The evacuation block in the main `agent()` loop changes from:

```
safe = [t for t in targets if _path_safe(...)]
best = max(safe, key=lambda t: t.production / (dist + ε))
```

To:

```
all_candidates = [(p, score(p)) for p in planets if p.id != mine.id and _path_safe(...)]
best = max(all_candidates, key=score)
# score(p): if p.owner == player → production / (dist + ε)
#            else                 → _roi(p, predicted_x, predicted_y, mine)
```

Predicted positions for orbiting planets and comets in the evacuation candidate pool are computed via `_converged_orbit_lead` / `_comet_two_pass` respectively.

#### 5. Experiment evaluation protocol

Each candidate experiment command:
```bash
uv run python eval.py --agent0 candidate_vX.py --agent1 agent_v32.py \
    --games 50 --jobs 4 \
    --reward-log experiments/009-candidate-X.jsonl
```

Post-run reward analysis:
```bash
uv run python reward_analysis.py experiments/009-candidate-X.jsonl
```

Report: win rate (primary gate), mean per-turn reward delta for agent0 vs agent1 (secondary, informational).

### data-model.md

*See [data-model.md](data-model.md) for entity definitions.*

### contracts/

*See [contracts/eval-cli.md](contracts/eval-cli.md) for the updated eval CLI contract.*

### Agent Context Update

CLAUDE.md plan reference updated to point to `specs/009-fix-comet-fleet-targeting/plan.md`.

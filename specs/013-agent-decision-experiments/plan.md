# Implementation Plan: Agent Decision Experiments

**Branch**: `013-agent-decision-experiments` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-agent-decision-experiments/spec.md`

## Summary

Run controlled single-variable experiments across the four live decision variables in
agent_v38 — target scoring formula, fleet sizing policy, garrison floor multiplier, and
source assignment policy — to identify which choices produce the highest win rate against
agent_v38. The best-performing variant from each experiment is then stacked into agent_v42.
Target: ≥60% win rate vs agent_v38 (50 games, seed 0). All results recorded in
`experiments/013-agent-decisions.md` before any promotion.

---

## Technical Context

**Language/Version**: Python 3.14 (repo requirement, uv-managed)

**Primary Dependencies**: `kaggle-environments>=1.28.0` (already installed); `numpy` and
`math` stdlib in agent files; `eval.py` harness already present in repo root

**Storage**: Flat files at repo root (`agent_v42.py`, variant scratch files); experiment
record at `experiments/013-agent-decisions.md`

**Testing**: `uv run python eval.py --agent0 <variant>.py --agent1 agent_v38.py --games 50 --seed 0`
(win rate). `make test` (smoke test vs random). Secondary metrics collected by reading
`--reward-log` JSONL output.

**Target Platform**: Local macOS development (evaluation), Kaggle submission sandbox
(inference — Principle VI compliant)

**Project Type**: Competitive game agent — rule-based heuristics, no ML training in this feature

**Performance Goals**: ≥60% win rate vs agent_v38 (50 games, seed 0); turn time <1 second

**Constraints**: Pure Python + stdlib/numpy only at runtime. No torch or ML inference.
All agent files must comply with Principle VI (Option A: self-contained stdlib imports only).
Each variant file must be runnable standalone via `make test`.

**Scale/Scope**: 4 experiments × ~4 variants each = ~16 variant eval runs. One combined
candidate (agent_v42). Results in a single experiment record.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reinforcement Learning First | ✅ Exempt | Constitution permits heuristic baseline agents. This feature improves the heuristic baseline; RL path (spec 011) remains the primary improvement track. |
| II. Fair Play & Rules Compliance | ✅ Pass | No engine modifications. All variants enforce actTimeout <1s (pure math/stdlib/numpy). |
| III. Manual Submissions Only | ✅ Pass | Kaggle submission explicitly out of scope for this feature. |
| IV. Experiment & Improvement Documentation | ✅ Pass | Combined experiment record `experiments/013-agent-decisions.md` required with a results table before any promotion. |
| V. Local Self-Play as Primary Evaluation Loop | ✅ Pass | 50-game eval vs agent_v38 with seed 0 is the gate for every variant. |
| VI. Submission Package Completeness | ✅ Pass | agent_v42 will be self-contained (Option A) — stdlib + kaggle_environments imports only. |

**Result**: All gates pass. Proceeding to implementation.

---

## Project Structure

### Documentation (this feature)

```text
specs/013-agent-decision-experiments/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
agent_v42.py             # Combined best-variant agent (stacked from all 4 experiments)

experiments/
└── 013-agent-decisions.md   # Combined variant comparison table
```

**Structure Decision**: No new directories. Variant scratch files are created at repo root
during experimentation (e.g., `agent_013_scoring_1.py`) and may be cleaned up after results
are recorded. agent_v42.py is the only permanent output at repo root.

---

## Phase 0: Research

### R-001: Target Scoring Formula — Current State

**Decision**: agent_v38 scores each target as:
```
ROI(t) = production(t)² × max(1, 100 - travel_turns) / max(1, t.ships + t.production × travel_turns + 1)
```
Travel time is computed using `fleet_speed(t.ships + 1)`. A small reward-blend term adds
`REWARD_ALPHA=0.1 × reward_estimate(t, ships_needed)` to the normalised ROI score.

**Why it may be suboptimal**: The quadratic production term dominates at high production
values but does not distinguish between planets that are affordable (low garrison) vs
expensive. The `100 - travel_turns` decay is linear and may undervalue very close
low-production planets early game, causing stagnation.

**Variants to test**:
- `013-scoring-1` (baseline clone): exact agent_v38 ROI — control
- `013-scoring-2` (production-first): score = `production(t) / (t.ships + 1)` — ignores
  distance entirely; prefers cheapest high-production target
- `013-scoring-3` (distance-gated): same as ROI but with a hard distance cap —
  only targets within `nearest_enemy_dist × 1.5` are eligible; forces early expansion
  to closest planets regardless of production
- `013-scoring-4` (linear-blend): `w_prod × prod_norm + w_dist × (1 - dist_norm)` where
  both are normalised to [0,1] by map max — removes the quadratic production term

**Rationale for alternatives**: The production-first variant (scoring-2) tests whether the
current time-decay term actively hurts (too much weight on far cheap planets). The
distance-gated variant (scoring-3) tests whether constraining target range helps early
expansion. The linear-blend (scoring-4) tests whether removing the quadratic production
term provides a smoother priority signal.

---

### R-002: Fleet Sizing Policy — Current State

**Decision**: agent_v38 sends exactly `target.ships + 1` for every capture attempt.

**Why it may be suboptimal**: The minimum-capture policy ignores:
1. Production accrual during flight: a planet with production 4 and ships 30 will have
   at least `30 + 4 × travel_turns` ships when the fleet arrives — if travel is 10 turns
   the minimum send of 31 will fail.
2. Simultaneous enemy sends: if an enemy fleet is already heading toward the same neutral
   planet, sending `target.ships + 1` will lose to a larger enemy fleet.

**Variants to test**:
- `013-fleet-1` (baseline): `ships_needed = target.ships + 1` — control
- `013-fleet-2` (production-buffered): `ships_needed = target.ships + 1 + target.production × estimated_travel_turns` — adds production accrual buffer
- `013-fleet-3` (race-aware): if an enemy fleet is detected heading toward the same target
  (angle alignment within RACE_EPSILON), `ships_needed = max(target.ships + 1, enemy_fleet_ships + 1 + target.production × remaining_turns)` — scales up to beat the race
- `013-fleet-4` (combined): production-buffered + race-aware applied together

**Key implementation note for production-buffered**: `estimated_travel_turns` is computed
as `distance_to_target / fleet_speed(ships_needed)`. Since ships_needed depends on travel
time and travel time depends on ships_needed, one iteration of the formula is sufficient
(close enough given ships_needed is bounded by production × travel which grows slowly).

---

### R-003: Garrison Floor — Current State

**Decision**: agent_v38 uses:
```
floor = max(GARRISON_FLOOR_FACTOR × source.production, threat.get(source.id, 0))
GARRISON_FLOOR_FACTOR = 3
```
The threat component adds incoming enemy fleet ships if a fleet's angle matches the planet.

**Why it may be suboptimal**: The multiplier 3 is a single untested constant. It was
inherited from Candidate O (which compared 3 vs lower values in one round), but was never
swept systematically across a range. A smaller multiplier frees more ships for offense; a
larger multiplier provides more defense. The optimal value is empirically unknown.

**Variants to test**:
- `013-floor-1` (factor=1): floor = `max(1 × production, threat)` — very aggressive
- `013-floor-2` (factor=2): floor = `max(2 × production, threat)` — moderately aggressive
- `013-floor-3` (factor=3): floor = `max(3 × production, threat)` — current baseline (control)
- `013-floor-4` (factor=5): floor = `max(5 × production, threat)` — conservative
- `013-floor-5` (dynamic): floor = `max(FACTOR(step) × production, threat)` where
  FACTOR(step) scales from 1 in early game (steps 0–100) to 4 in late game (steps 300+),
  with linear interpolation — allows aggressive early expansion without late-game exposure

**Note**: The dynamic variant (floor-5) is the most interesting hypothesis — early game is
when planet-racing matters most, and the agent can afford a low floor then.

---

### R-004: Source Assignment Policy — Current State

**Decision**: agent_v38 uses a "single best sender" rule (Candidate D). For each target,
the one owned planet with the best `distance / surplus` score is designated sender.
No other owned planet is allowed to target that planet in the same turn.

**Why it may be suboptimal**: The single-sender rule means the agent can never deliver
concentrated force to a well-defended target. This is fine for neutral expansion (targets
are weakly defended) but makes it unable to attack strong enemy planets efficiently.

**Why previous multi-sender approaches failed** (feature 012): They forced ALL owned
planets to target the same destination, ignoring individual garrison floors. Planets drained
below safe levels, and when that one attempt failed, the agent had no garrison left.

**Correct multi-sender design**: A planet may contribute to a coordinated attack only if
its contribution does not violate its own garrison floor. The coordination is opt-in by
surplus availability, not forced.

**Variants to test**:
- `013-assign-1`: single best sender (current baseline — control)
- `013-assign-2`: surplus-gated multi-sender — any owned planet with `surplus > MIN_CONTRIB`
  may additionally send to the highest-priority target even if it is not the best sender.
  `MIN_CONTRIB = 10` ships as threshold. Primary sender still determined by best-sender
  logic; additional senders are secondary. Each additional sender sends only `MIN_CONTRIB`
  ships (not their full surplus) to ensure fleet diversity is maintained.
- `013-assign-3`: top-2 senders — instead of only the best sender, allow the best AND
  second-best sender to target the same destination. Garrison floor enforced for both.
  Both send `target.ships / 2 + 1` each (split the capture cost).

---

## Phase 1: Design

### Variant Isolation Design

Each variant is implemented as a minimal diff from agent_v38. The implementation approach:

1. Copy `agent_v38.py` to a variant file (e.g., `agent_013_scoring_2.py`)
2. Change only the single function or constant corresponding to the variable under test
3. Keep all other agent logic identical to agent_v38

This ensures that any win-rate change is attributable to the single changed variable.

The final agent_v42 stacks all four best variants by applying each change to a single
consolidated file.

### Combination Strategy

Once the best variant from each experiment is identified:
- If all four best variants have independent code paths (no shared functions), they stack
  safely by combining their diffs into a single agent file.
- If two best variants modify the same code section (e.g., both scoring and fleet-sizing
  affect the candidate scoring logic), the combination must be designed carefully —
  document the interaction in the experiment record.

### Experiment Record Structure

`experiments/013-agent-decisions.md` format:

```markdown
## Experiment A: Target Scoring

| Variant | Win Rate | Avg Planets @ step 100 | Avg Prod Rate @ step 150 | Notes |
|---------|----------|------------------------|--------------------------|-------|
| baseline (013-scoring-1) | ~50% | ... | ... | control |
| ...     | ...      | ...                    | ...                      |       |

**Best**: [variant], [win rate]

## Experiment B: Fleet Sizing
...

## Experiment C: Garrison Floor
...

## Experiment D: Source Assignment
...

## Combined (agent_v42)
| Metric | agent_v42 | agent_v38 |
|--------|-----------|-----------|
| Win rate | ... | baseline |
...
```

### Data Model

See [data-model.md](data-model.md) for entity definitions.

### No External Interfaces

This feature produces standalone Python agent files and a Markdown experiment record. There
are no APIs, CLIs, or network interfaces to contract. No `contracts/` directory is created.

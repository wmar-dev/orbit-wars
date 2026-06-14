---
description: "Task list for Advanced Agent Techniques (Round 8)"
---

# Tasks: Advanced Agent Techniques (Round 8)

**Input**: Design documents from `specs/031-advanced-agent-techniques/`

**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (user stories), [research.md](research.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md)

**Tests**: No unit-test tasks. In this competition-agent project, the "test" of each increment is a **self-play + benchmark eval** (`eval.py h2h --swap`), which appears as explicit evaluation tasks within each candidate phase.

**Organization**: This is an experiment round. The independently-testable increments are the three **candidate techniques** (A/B/C), each implemented behind an isolated toggle on `agent_v69.py`. Each candidate serves both P1 user stories — **US1** (win >0% vs the `slawekbiel` benchmark) and **US2** (beat `agent_v68` ≥52% in self-play) — and must pass the **US3** safety gate (zero sun/OOB losses, within time budget). Tasks are tagged with the user stories they serve.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files / independent runs, no dependency on an incomplete task)
- **[Story]**: US1 (benchmark wall), US2 (beat current best), US3 (safety/legality)
- All paths are repo-root-relative. `agent_v68.py` is **frozen** — never edit it.

## User Story → Phase map

- **US1 / US2** are *evaluation axes of the same code*, so every candidate phase (3–5) and the combination phase (6) carries both labels.
- **US3** is a cross-cutting gate verified inside every candidate phase and the combination phase.

---

## Phase 1: Setup (fork + toggle scaffolding)

**Purpose**: Create the working agent file and the disabled-by-default toggles so `agent_v69 ≡ agent_v68` until a candidate is enabled.

- [X] T001 Fork the frozen baseline: `cp agent_v68.py agent_v69.py` (do not modify `agent_v68.py`)
- [X] T002 In `agent_v69.py`, add four constants in the tunable-constants block, committed default OFF: `GLOBAL_ALLOC_ENABLED = False`, `DEEP_SEARCH_ENABLED = False`, `DEEP_SEARCH_BUDGET_MS = 700`, `REGROUP_ENABLED = False`; update the module docstring to describe Round 8 Candidates A/B/C
- [X] T003 Equivalence sanity check: with all new toggles `False`, run `uv run python eval.py h2h --agent0 agent_v69.py --agent1 agent_v68.py --games 20 --swap --jobs 4` and confirm ~50% (functional equivalence to `agent_v68`)

**Checkpoint**: `agent_v69.py` exists, compiles, and is behavior-identical to `agent_v68.py`.

---

## Phase 2: Foundational (replay-driven design confirmation) — BLOCKS candidate implementation

**Purpose**: Confirm/refine the source-derived Candidate A/B/C hypotheses against real game evidence before writing decision logic (research.md R1 confirmation step). No candidate code is written until this completes.

**⚠️ CRITICAL**: Candidate phases 3–5 must not begin until T005 confirms or re-ranks the candidates.

- [X] T004 Capture ≥5 fresh baseline-vs-benchmark replays: `uv run python record_replays.py --agent0 agent_v68.py --agent1 opponent_agents/slawekbiel_agent.py --games 5 --slug slawekbiel` (verify `replays/replay_slawekbiel_*.json` written; confirm `slawekbiel_agent` loads under torch 2.12.0)
- [X] T005 Run the `analyze-replay` skill on the captured replays; write `experiments/2026-06-14-round8-replay-analysis.md` recording the decisive divergence pattern and confirming (or re-ranking) Candidates A (global allocation), B (deeper search), C (regroup repositioning) per research.md R1

**Checkpoint**: Candidate designs are evidence-confirmed; the three code regions in `agent_v69.py` are identified.

---

## Phase 3: Candidate A — Global coordinated allocation (Priority: P1) 🎯 MVP

**Goal**: Replace `agent_v68`'s per-planet greedy target claiming with a joint (source→target) assignment that resolves conflicts globally, closing the largest structural gap vs `slawekbiel`.

**Independent Test**: With only `GLOBAL_ALLOC_ENABLED = True`, the agent beats `agent_v68` ≥52% over 50 `--swap` self-play games AND does not regress below 0% vs `slawekbiel` over 30 `--swap` games, with zero safety/timing violations.

- [X] T006 [US1] [US2] Implement Candidate A in `agent_v69.py`: gate the target-claiming step (the `claimed_targets` per-planet loop in `_greedy_moves`) behind `GLOBAL_ALLOC_ENABLED` — when on, score all (source planet, candidate target) pairs and select a globally-coherent assignment (best-fit source per target; redirect remaining sources), composing with (not overriding) the existing opening-rush `CANDIDATE_1` candidate; pure-Python only, no new imports
- [X] T007 [US2] Self-play eval: `uv run python eval.py h2h --agent0 agent_v69.py --agent1 agent_v68.py --games 50 --swap --jobs 4` (only `GLOBAL_ALLOC_ENABLED=True`); record win rate
- [X] T008 [P] [US1] Benchmark eval: `uv run python eval.py h2h --agent0 agent_v69.py --agent1 opponent_agents/slawekbiel_agent.py --games 30 --swap --jobs 4`; record win rate vs `agent_v68`'s 0%
- [X] T009 [US3] Safety/timing gate: from the T007/T008 game logs confirm zero sun losses, zero OOB losses, and zero per-turn budget breaches; record PASS/FAIL verdict for Candidate A in the round experiment log

**Checkpoint**: Candidate A has a recorded verdict on both axes and the safety gate.

---

## Phase 4: Candidate B — Deeper time-bounded search (Priority: P1)

**Goal**: Trade compute for strength via anytime deeper/wider lookahead, bounded by a wall clock with a guaranteed safe fallback.

**Independent Test**: With only `DEEP_SEARCH_ENABLED = True`, beats `agent_v68` ≥52% self-play and does not regress vs `slawekbiel`, with every turn completing under `DEEP_SEARCH_BUDGET_MS` (no forfeits).

- [X] T010 [US1] [US2] Implement Candidate B in `agent_v69.py`: wrap `_beam_search` behind `DEEP_SEARCH_ENABLED` with anytime iterative deepening/widening (or time-bounded MCTS over the existing forward sim) that loops while `elapsed < DEEP_SEARCH_BUDGET_MS`, then returns the best move found; if no completed search exists, fall back to `agent_v68`'s greedy/beam move (FR-010 graceful degradation); pure-Python only
- [X] T011 [US3] Timing validation: `uv run python eval.py h2h --agent0 agent_v69.py --agent1 agent_v68.py --games 3 --verbose` on dense boards; confirm p99 per-turn < `DEEP_SEARCH_BUDGET_MS` + fallback margin and zero forfeits (SC-005)
- [X] T012 [US2] Self-play eval: 50 `--swap` games vs `agent_v68` (only `DEEP_SEARCH_ENABLED=True`); record win rate
- [X] T013 [P] [US1] Benchmark eval: 30 `--swap` games vs `slawekbiel`; record win rate
- [X] T014 [US3] Safety gate: confirm zero sun/OOB losses across T011–T013 logs; record Candidate B verdict in the experiment log

**Checkpoint**: Candidate B verdict recorded with explicit timing evidence.

---

## Phase 5: Candidate C — Regroup/reinforcement repositioning (Priority: P1)

**Goal**: Add a pre-emptive regroup gradient that moves rear-planet surplus toward stressed/threatened owned planets — distinct from R4's failed reactive `DEFENSE_INTERCEPT`.

**Independent Test**: With only `REGROUP_ENABLED = True`, beats `agent_v68` ≥52% self-play and does not regress vs `slawekbiel`, zero safety/timing violations.

- [X] T015 [US1] [US2] Implement Candidate C in `agent_v69.py`: behind `REGROUP_ENABLED`, add a repositioning pass that ranks owned planets by stress (reachable enemy mass) and dispatches surplus from low-stress rear planets up the gradient toward high-stress planets, only over sun/OOB-safe paths (reuse `_path_safe`), without consuming ships reserved by the garrison floor; pure-Python only
- [X] T016 [US2] Self-play eval: 50 `--swap` games vs `agent_v68` (only `REGROUP_ENABLED=True`); record win rate
- [X] T017 [P] [US1] Benchmark eval: 30 `--swap` games vs `slawekbiel`; record win rate
- [X] T018 [US3] Safety gate: confirm zero sun/OOB losses and within-budget timing across T016/T017 logs; record Candidate C verdict in the experiment log

**Checkpoint**: All three candidates have recorded verdicts on both axes + safety.

---

## Phase 6: Combination + benchmark re-verification (Priority: P1)

**Goal**: Combine every passing candidate and re-verify on both axes — the round's adoption decision (FR-007, FR-012).

**Independent Test**: With all PASSING candidates' toggles `True`, the combination beats `agent_v68` ≥52% self-play AND shows no benchmark regression (≥0%, ideally >0% per SC-001).

- [X] T019 [US2] Enable every candidate that PASSED Phases 3–5 (set its toggle `True`); run combined self-play: 50 `--swap` games vs `agent_v68`; record win rate
- [X] T020 [P] [US1] Combined benchmark re-check: 30 `--swap` games vs `slawekbiel`; record win rate (the SC-001 / SC-003 confirmation)
- [X] T021 [P] [US3] Combined safety/regression sweep: `uv run python eval.py opponents --agent agent_v69.py --games 20`; confirm zero sun/OOB losses and no regression vs other downloaded opponents
- [X] T022 [US1] [US2] Decide outcome per data-model.md state machine: if combo ≥52% self-play AND no benchmark regression → adopt `agent_v69` as new best; else retain `agent_v68` (optionally keep the single best passing candidate enabled if it alone clears the bar). Set the committed toggle state in `agent_v69.py` to the adopted config (all `False` if nothing passed)

**Checkpoint**: Round outcome decided and the committed `agent_v69.py` toggle state reflects it.

---

## Phase 7: Polish — documentation & adoption

**Purpose**: Record results and, only on a confirmed new best, update the project pointers (FR-011, FR-013).

- [X] T023 Write `experiments/2026-06-14-experiments-round8.md`: per-candidate self-play/benchmark/timing/safety table, combination result, benchmark re-check, and the adopt/retain conclusion (Principle IV — required before any submission)
- [X] T024 Pre-submission import check (Constitution VI): `grep -n "^from \|^import " agent_v69.py | grep -v "kaggle_environments\|math\|random\|copy\|time"` → expect no output (Option A self-contained)
- [X] T025 [P] IF a new best was adopted: update `README.md` Agents table (add `agent_v69` row, **bold** it as current best, record win rates) per CLAUDE.md
- [X] T026 [P] IF a new best was adopted: update `Makefile` `AGENT` and `RENDER_AGENT` to `agent_v69.py` per CLAUDE.md
- [X] T027 [P] IF a new best was adopted: update the auto-memory lineage note (`project_agent_lineage_nontransitive.md` + `MEMORY.md`) — new best `agent_v69`, re-verify vs v69 next round, record its `slawekbiel` win rate

---

## Dependencies & execution order

- **Phase 1 (T001–T003)** → must finish before everything (creates `agent_v69.py`).
- **Phase 2 (T004–T005)** → blocks all candidate phases (confirms designs).
- **Phases 3, 4, 5** → each depends only on Phase 2; the three candidates touch **independent code regions**, so they can be implemented in parallel branches, but each candidate's own eval tasks depend on its implementation task.
- **Phase 6 (T019–T022)** → depends on all of Phases 3–5 (needs each verdict).
- **Phase 7 (T023–T027)** → depends on Phase 6 (T025–T027 are conditional on adoption).

## Parallel execution opportunities

- Within a candidate phase, the **benchmark eval is `[P]`** with the self-play eval (independent harness runs): e.g., T007 + T008, T012 + T013, T016 + T017 can run concurrently with `--jobs`.
- In Phase 7, T025/T026/T027 are `[P]` (different files) once adoption is decided.
- Candidate *implementations* (T006, T010, T015) are independent code regions and may be developed in parallel, but should be **evaluated in isolation** (only one toggle `True`) to attribute effect.

## Implementation strategy (MVP first)

1. **MVP = Phase 1 + Phase 2 + Phase 3 (Candidate A)** — Candidate A closes the single largest gap vs `slawekbiel`; if it alone moves the benchmark off 0% and beats `agent_v68` ≥52%, it is a shippable Round 8 result on its own.
2. Add Candidates B and C as independent increments; each either passes (joins the combination) or is documented as a wash (toggle stays `False`).
3. Phase 6 combines passers; Phase 7 adopts only on a confirmed, twice-verified improvement, else retains `agent_v68` and documents the negative round (Rounds 5/7 precedent).

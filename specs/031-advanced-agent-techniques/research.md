# Phase 0 Research: Advanced Agent Techniques (Round 8)

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Date**: 2026-06-13

This round's research is shaped by one decisive observation: `agent_v68` loses **0/30** to `slawekbiel_agent`, and that opponent's source (`# slawekbiel / the-producer-agent`) exposes *why*. The three research questions below select techniques that close the specific structural gaps that source reveals, bound their cost, and define the adoption protocol.

## Benchmark opponent analysis (input to all three questions)

`opponent_agents/slawekbiel_agent.py` (369 lines) + an `orbit_lite` package. It is **not** a learned policy — `torch` is used only as a vectorized math engine (`torch.no_grad()` at the entry point; no parameter file, no forward net). Its strength comes from three algorithmic properties, all absent in `agent_v68`:

1. **Global candidate scoring** (`_candidate_indices`, `score_candidates`, `_greedy_select`, `build_target_shortlist`): every (source planet → target) launch is scored *simultaneously* across the whole board, then a global greedy selection commits a coherent set — rather than `agent_v68`'s per-planet loop that claims targets one mine at a time (`claimed_targets` in `_greedy_moves`).
2. **Regroup gradient** (`_plan_regroup`, "rank owned planets by how stressed they are, move ships up the gradient"): surplus ships flow from safe rear planets toward stressed front planets *before* contact — coordinated repositioning, not reactive defense.
3. **Reinforcement timing** (`reinforcement_timing_factor`, `capture_floor`, `safe_drain`): captures and reinforcements are timed so a planet is neither over-drained nor reinforced too late.

`agent_v68`, by contrast: per-planet greedy claim → beam search over a handful of candidate move-sets (`BEAM_K=3`, `NPLY_BEAM_WIDTH=8`, `SEARCH_DEPTH=10`) with a position-based opponent model. Its only coordination is `SPLINTER_DISPATCH` (send leftover surplus to a nearby cheap neutral) and `CANDIDATE_1` (opening rush). The structural gap is **joint multi-planet allocation + pre-emptive repositioning**, exactly slawekbiel's edge — and reproducible in pure Python.

---

## R1 — Which advanced techniques to implement

**Decision**: Three candidates, each a distinct *technique class* (per FR-002's menu), each mapped to a slawekbiel gap and each verified distinct from a prior failed candidate.

| Candidate | Technique class | Closes gap | Distinct from prior failure because |
|-----------|-----------------|------------|--------------------------------------|
| **A. Global coordinated allocation** (`GLOBAL_ALLOC_ENABLED`) | Multi-planet coordinated strategy | slawekbiel's global candidate scoring vs v68's per-planet `claimed_targets` loop | `MULTI_DISPATCH_ENABLED` (R6, 50% wash) merely *removed* single-sender serialization — it let every planet pick its own best target independently with no global conflict resolution. Candidate A is the opposite: it adds a *joint* assignment that scores all (source,target) pairs and resolves conflicts globally (one target served by the best-fit source; remaining sources redirected), which prior rounds never implemented. |
| **B. Deeper time-bounded search** (`DEEP_SEARCH_ENABLED`) | Stronger/deeper lookahead search | v68's fixed shallow beam (`BEAM_K=3`, width 8) under-searches; slawekbiel commits coherent multi-move plans | No prior round varied search *budget*; all used the fixed beam. Candidate B adds iterative deepening / wider beam (or time-bounded MCTS over the existing forward sim) until a wall-clock bound, then falls back to v68's move. This is a compute-for-strength trade never tested, not a re-run of a constant tweak. |
| **C. Regroup/reinforcement repositioning** (`REGROUP_ENABLED`) | Richer evaluation + coordinated repositioning | slawekbiel's `_plan_regroup` gradient; v68 has no ship repositioning at all | `DEFENSE_INTERCEPT_ENABLED` (R4, 48%/45% wash) was *reactive interception* of a specific incoming enemy fleet. Candidate C is *pre-emptive gradient repositioning*: rank owned planets by stress (reachable enemy mass), move rear surplus up the gradient regardless of any single detected fleet. Different trigger, different mechanism. |

**Rationale**: All three target the *one* opponent the lineage cannot beat, each advances a different technique class (satisfying SC-006's "≥2 qualitatively advanced"), and each is explicitly differentiated from the documented R4/R6 failure traps (FR-014). Implementing three (not two) hedges against one or two washing out while still producing a publishable round.

**Alternatives considered**:
- *Learned value function / tiny inlined neural net*: rejected — FR-009 forbids torch/numpy in the submitted agent, and a pure-Python matmul value net is both slow (time-budget risk) and a de-facto RL effort better suited to a dedicated round (Principle I).
- *Opponent-model overhaul (v4)*: rejected as a headline candidate — `OPPONENT_MODEL_V3` already regressed to 34% (R4); model accuracy is a smaller lever than the structural allocation gap. May be revisited only if A/B/C all wash.
- *Re-tuning beam constants*: rejected — this is exactly the incremental approach Rounds 5–7 showed has plateaued; out of scope by the spec's framing.

**Phase A confirmation step**: Before freezing the three designs, capture ≥5 fresh `agent_v68`-vs-`slawekbiel` replays and run the `analyze-replay` skill. If the decisive divergence pattern contradicts the source-based hypothesis (e.g., losses are dominated by something other than coordination/repositioning), re-rank the candidates accordingly. The source analysis is the prior; the replays are the evidence.

---

## R2 — Bounding Candidate B within the time budget

**Decision**: Candidate B wraps the existing `_beam_search` in a wall-clock guard. It iteratively increases search effort (deepening / widening, or expanding MCTS rollouts over the same forward-sim) while `elapsed < DEEP_SEARCH_BUDGET_MS` (default 700 ms, leaving ≥300 ms headroom under the 1 s `actTimeout`). On budget exhaustion it returns the best move found so far; if *no* completed search exists yet, it returns `agent_v68`'s greedy/beam move unchanged. This guarantees a valid, safe move every turn (FR-010, FR-008).

**Rationale**: `agent_v68` already carries `SEARCH_TIMEOUT_MS=800` and `time` imports, so a wall-clock guard is idiomatic and low-risk. Anytime iterative deepening makes the strength↔budget trade tunable via a single constant and degrades gracefully on worst-case boards (max planets/fleets) — the explicit Edge Case in the spec. Safety filters (`_path_safe`, in-bounds checks) run inside candidate generation, so any returned move — including the fallback — is already sun/OOB-safe.

**Alternatives considered**:
- *Fixed deeper beam with no clock guard*: rejected — risks `actTimeout` forfeits on dense boards (Principle II violation).
- *Full minimax to fixed depth*: rejected — branching factor (multi-planet move-sets) is far too large for reliable sub-second fixed-depth search; anytime beam/MCTS is the safe shape.

**Validation**: Per-turn timing is logged across a full diagnostic game; p99 must stay < `DEEP_SEARCH_BUDGET_MS` + measured fallback cost, with zero turns exceeding the budget (SC-005).

---

## R3 — Evaluation, combination, and adoption protocol

**Decision**: Two-axis evaluation per candidate, then combine-and-reverify.

1. **Self-play axis**: `eval.py h2h --agent0 agent_v69.py --agent1 agent_v68.py --games 50 --swap --jobs 4`, with only that candidate's toggle `True`. Pass ≥ **52%** (consistent with Rounds 6–7).
2. **Benchmark axis**: `eval.py h2h --agent0 agent_v69.py --agent1 opponent_agents/slawekbiel_agent.py --games 30 --swap`. Must **not regress** below `agent_v68`'s 0%; SC-001 targets strictly **>0%**.
3. **Adoption (FR-006)**: a candidate passes only if it clears the self-play bar AND shows no benchmark regression. Passers are combined (all passing toggles `True`); the combination is re-run on both axes (50 self-play + 30 benchmark). The combined config is adopted as new current best only if it beats `agent_v68` ≥52% self-play (FR-012). If nothing passes, `agent_v68` is retained and the negative result documented.

**Rationale**: The benchmark axis is the round's whole point (SC-001/SC-003) and guards against self-play overfitting — a candidate could beat v68 in self-play by exploiting v68's specific blind spots while staying 0% vs the real benchmark. Requiring both raises decision confidence toward Principle VII's 95% bar without a prohibitive game count (~320 games total).

**Statistical note**: 30 swap games vs the benchmark is a coarse but decisive instrument for the 0%→>0% question — a single win already falsifies "hard-capped at 0%." For the self-play 52% bar, 50 swap games match the established lineage protocol; the combination's benchmark re-check is the tie-breaker when self-play is near the threshold.

**Alternatives considered**:
- *Self-play axis only* (Rounds ≤5 style): rejected — it is exactly what let the lineage plateau at 0% vs the benchmark; SC-001/SC-003 require the benchmark axis.
- *100+ games per candidate*: rejected — diminishing confidence return for ~2× the compute; 50/30 is the established, sufficient sample, with the combination re-check as the second confirmation.

---

## Open risks carried into Phase 1

- **Candidate A scope creep**: a full optimal assignment (Hungarian) is O(n³) but n≤~30, so cost is negligible; the risk is *behavioral* — global reassignment may starve the opening rush (`CANDIDATE_1`). Mitigation: gate Candidate A to compose with, not override, the existing opening-rush candidate; verify in self-play.
- **Combination interaction**: A (global allocation) and C (repositioning) both move ships; they touch different planets (attackers vs idle rear) but could contend. The combination run (R3) is the explicit check.
- **Replay evidence may re-rank candidates**: handled by the Phase A confirmation step in R1.

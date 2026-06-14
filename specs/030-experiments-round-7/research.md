# Phase 0 Research: Experiments Round 7

## R1: How should the Round 7 benchmark opponent be selected, and how is the `slawekbiel`/`torch` blocker handled?

**Decision**: Two steps.

1. **One-time `slawekbiel` unlock attempt** (documented either way):
   ```bash
   uv pip install torch    # expected to fail: no torch wheel for cpython-3.14
   ```
   If it succeeds, `slawekbiel_agent` joins the sweep. If it fails (the expected outcome), record the error in `experiments/2026-06-1X-round7-opponent-matrix.md` and proceed without it. Do NOT add `torch` to the agent's own dependencies — it is local-tooling-only for opponent replay, and the agent must stay stdlib + `kaggle_environments` (Principle VI).

2. **Opponent sweep** using the existing harness, which already enumerates `KNOWN_OPPONENTS` and skips/fails-loud on unloadable ones:
   ```bash
   uv run python eval.py opponents --agent agent_v64.py --games 20
   ```
   Plus two intra-lineage sparring pairings (to detect local-opponent saturation per FR-001 / US1 acceptance scenario 3):
   ```bash
   uv run python eval.py h2h --agent0 agent_v64.py --agent1 agent_v58.py --games 20 --jobs 4 --swap
   uv run python eval.py h2h --agent0 agent_v64.py --agent1 agent_v60.py --games 20 --jobs 4 --swap
   ```
   The opponent against which `agent_v64` has the **lowest** win rate becomes the Round 7 benchmark opponent.

**Rationale**: Round 6's replay analysis was run vs `agent_v60` (the only fallback considered), which `agent_v64` beats 80% — almost no losing games to learn from. `eval.py opponents` already sweeps all 7 downloaded opponents in one command; picking the *hardest loadable* one maximizes the number of informative (lost/contested) games feeding Phase B. The two sparring pairings catch the saturation case where every external opponent is weak.

**Alternatives considered**:
- Stub `slawekbiel`'s `torch` import with a numpy/pure-python shim — rejected as high-effort and risky (its policy is a tensor pipeline; a partial stub would change its behavior, making it a different, non-representative opponent). A clean `pip install` is the only faithful unlock; if it fails, drop it.
- Pin a Python version with torch wheels (e.g., 3.11) in a parallel venv just for `slawekbiel` replay — rejected as out of scope for this round; noted as a follow-up in the spec's Edge Cases.
- Use the FFA `4p` mode against mixed opponents to pick the benchmark — rejected; 1v1 `--swap` h2h gives a cleaner, reproducible per-opponent win rate for selection, and Phase B replay analysis is designed for 1v1 divergence tracking.

**Acceptance threshold** (per US1 scenario 3): if the lowest win rate is still ≥65%, accept it but note local-opponent saturation and supplement Phase B with self-play replays vs `agent_v58`/`agent_v60`.

---

## R2: How should Phase B (replay generation + analysis) be run?

**Decision**: Use the existing `record_replays.py` (it already writes the exact JSON shape the `analyze-replay` skill consumes, including per-turn planet counts, ship totals, and divergence-turn computation):

```bash
uv run python record_replays.py --our-agent agent_v64.py --opponent opponent_agents/<BENCHMARK>_agent.py --games 5 --out-dir replays
```

Then invoke the analysis skill on the produced files:

```text
/analyze-replay replays/replay_<BENCHMARK>_*.json
```

which writes `experiments/2026-06-1X-replay-analysis.md` with win rate, median divergence turn, the decisive divergence window, ≥3 behavioral differences, and 2–3 candidate directions (each with hypothesis, predicted effect, risk, novelty check) per FR-003/FR-004/SC-002.

**Rationale**: `record_replays.py` is purpose-built for this (vs the ad-hoc inline `env.run` script used in Round 6's quickstart) — it handles `--swap` side alternation, reorders to `[our, opponent]`, and emits the analyze-replay schema directly, eliminating a format-mismatch risk. The `analyze-replay` skill already implements every statistic FR-003 requires, so Phase B is "record, then invoke the skill."

**Candidate-quality guardrails** (FR-004/FR-005, from Round 6's post-mortem):
- Any candidate resembling **affordable fallback** (Round 6 Candidate 1, 6% — severe regression) MUST first isolate or respect the `MULTI_TURN_PLAN_ENABLED` beam search's deliberate "wait and accumulate" choice; the documented failure was greedily short-circuiting that lookahead. A revisit is only valid if it gates on "the beam search did NOT prefer waiting" or disables the interaction to isolate it.
- Any candidate resembling **garrison-floor scaling by global ship ratio** (Round 6 Candidate 2, 48% — wash) MUST be *local/per-planet and threat-detection-based* rather than a single global multiplier, per Round 6's explicit follow-up lead.
- Each candidate's novelty check enumerates the adopted/discarded mechanics across `agent_v57`–`agent_v67` (early/multi-planet/splinter dispatch, dynamic garrison, weighted beam eval, multi-turn plan skip, multi-source attacks, fleet-size convergence, FFA adaptation, endgame focus, affordable fallback, global relative-strength garrison scaling).

**Alternatives considered**:
- Reusing Round 6's inline `env.run` + `env.toJSON()` snippet — rejected in favor of `record_replays.py` for schema fidelity and `--swap` handling.
- Downloading fresh Kaggle FFA episodes — rejected: 4-player, unknown opponents, noisier and non-reproducible for 1v1 divergence analysis.

**Fallback** (per Edge Cases): if the chosen benchmark opponent fails to load at record time, fall back to the next-hardest loadable opponent from the R1 sweep; if all external opponents are saturated (≥65%), additionally record `agent_v64` vs `agent_v58`/`agent_v60` self-play replays.

---

## R3: How should Phase C (candidate implementation, eval, combination, and benchmark re-check) be run?

**Decision**: Copy `agent_v64.py` to `agent_v68.py` (next version after `agent_v67.py`, confirmed unused). Add one independent toggle constant per candidate (`CANDIDATE_1_ENABLED`, …), defaulting `False`, each gating an independent code region. Evaluate:

```bash
# Each candidate alone (its toggle True, others False):
uv run python eval.py h2h --agent0 agent_v68.py --agent1 agent_v64.py --games 50 --jobs 4 --swap --timing

# Combination (all passing toggles True):
uv run python eval.py h2h --agent0 agent_v68.py --agent1 agent_v64.py --games 50 --jobs 4 --swap --timing

# Benchmark re-check of the resulting best config (NEW this round, FR-009):
uv run python eval.py h2h --agent0 agent_v68.py --agent1 opponent_agents/<BENCHMARK>_agent.py --games 30 --jobs 4 --swap
```

A candidate passes at ≥52% win rate vs `agent_v64`. `--timing` gives p50/p95/p99 to confirm the <100ms p99 / <800ms budget (SC-006). The benchmark re-check confirms the self-play win does not regress against the tougher opponent (SC-005): the best config's win rate vs `<BENCHMARK>` must be ≥ `agent_v64`'s baseline win rate vs the same opponent (from R1).

**Rationale**: Matches the toggle-constant pattern established across `agent_v61`/`agent_v62`/`agent_v65`/`agent_v67` and the independent-then-combined sequence used in Rounds 2–6. The benchmark re-check is the one genuinely new step, added to satisfy Principle VII (95% confidence) by validating against a second, harder signal beyond self-play — directly addressing the self-play-only weakness that let Round 6's neutral candidate look plausible.

**Alternatives considered**:
- Separate files per candidate — rejected; the single-file toggle pattern makes the combination step "enable both toggles" rather than a 3-way merge, and is the established convention.
- Skipping the benchmark re-check to save games — rejected; it is the round's primary confidence improvement over Round 6 and is cheap (30 games).

---

## Resolved Unknowns

No `[NEEDS CLARIFICATION]` markers remain. Two questions are intentionally deferred to execution because they are *outputs* of phases, not planning inputs:
- *Which opponent is the Round 7 benchmark?* — output of Phase A (R1).
- *What are the 2–3 candidate directions?* — output of Phase B (R2).

The one true environmental risk (`torch` uninstallable on Python 3.14, blocking `slawekbiel`) is resolved by design: the round selects the hardest *loadable* opponent regardless, and documents the `slawekbiel` outcome as a known limitation.

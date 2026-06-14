# Quickstart: Experiments Round 7

Baseline / fork point: **`agent_v64.py`** (current best). New agent: **`agent_v68.py`**.

## Phase A — Select the benchmark opponent

```bash
# 1. One-time attempt to unlock slawekbiel (expected to fail on Python 3.14 — record either way).
uv pip install torch || echo "torch unavailable for Python 3.14 — slawekbiel stays unloadable (documented)"

# 2. Sweep agent_v64 vs all known (loadable) opponents.
uv run python eval.py opponents --agent agent_v64.py --games 20

# 3. Intra-lineage sparring (saturation check).
uv run python eval.py h2h --agent0 agent_v64.py --agent1 agent_v58.py --games 20 --jobs 4 --swap
uv run python eval.py h2h --agent0 agent_v64.py --agent1 agent_v60.py --games 20 --jobs 4 --swap
```

Record all win rates in `experiments/2026-06-1X-round7-opponent-matrix.md`. Pick the opponent with the **lowest** `agent_v64` win rate as `<BENCHMARK>`. If the lowest is still ≥65%, accept it but flag local-opponent saturation and plan to supplement Phase B with `agent_v58`/`agent_v60` self-play replays.

## Phase B — Fresh replay analysis vs the benchmark opponent

```bash
# Record >=5 games of agent_v64 vs the chosen benchmark (writes analyze-replay-format JSON).
uv run python record_replays.py --our-agent agent_v64.py \
    --opponent opponent_agents/<BENCHMARK>_agent.py --games 5 --out-dir replays
```

Then run the analysis skill:

```text
/analyze-replay replays/replay_<BENCHMARK>_*.json
```

This writes `experiments/2026-06-1X-replay-analysis.md` with win rate, median divergence turn, the decisive divergence window, ≥3 behavioral differences, and 2–3 candidate directions (hypothesis + predicted effect + risk + novelty check). For each candidate:
- Confirm it is distinct from mechanics in `agent_v57`–`agent_v67`.
- If it resembles **affordable fallback**, it MUST respect/isolate the `MULTI_TURN_PLAN_ENABLED` "wait and accumulate" choice (Round 6 Candidate 1 regressed to 6% without this).
- If it resembles **garrison-floor scaling**, it MUST be *local/per-planet threat-based*, not a global ship-ratio multiplier (Round 6 Candidate 2 was a 48% wash).

## Phase C — Implement, evaluate, combine, benchmark re-check

```bash
cp agent_v64.py agent_v68.py
# Add CANDIDATE_1_ENABLED / CANDIDATE_2_ENABLED [/ CANDIDATE_3_ENABLED] toggles (default False)
# + gated logic per the Phase B findings, each in an independent code region.

# Each candidate alone (only its toggle True):
uv run python eval.py h2h --agent0 agent_v68.py --agent1 agent_v64.py --games 50 --jobs 4 --swap --timing
# (repeat per candidate)

# Combination (all passing toggles True):
uv run python eval.py h2h --agent0 agent_v68.py --agent1 agent_v64.py --games 50 --jobs 4 --swap --timing

# Benchmark re-check of the resulting best config (NEW this round):
uv run python eval.py h2h --agent0 agent_v68.py --agent1 opponent_agents/<BENCHMARK>_agent.py --games 30 --jobs 4 --swap
```

Pass bar per candidate / combination: **≥52%** vs `agent_v64`. The benchmark re-check must show the best config's win rate vs `<BENCHMARK>` is **≥ `agent_v64`'s baseline** vs the same opponent (no regression). Confirm `--timing` p99 < 100ms and zero sun/OOB losses.

Record everything in `experiments/2026-06-1X-experiments-round7.md`.

## Closing out (per CLAUDE.md)

- **If the best config passes** (≥52% vs `agent_v64`, no benchmark regression, p99 < 100ms, 0 sun/OOB losses): bold `agent_v68.py` as current best in README's Agents table and set Makefile `AGENT`/`RENDER_AGENT := agent_v68.py`.
- **If nothing passes**: leave all toggles `False` (`agent_v68 ≡ agent_v64`), keep `agent_v64.py` bolded, set `AGENT`/`RENDER_AGENT` to `agent_v64.py` (unchanged), and document the discarded candidates with their win rates (cf. `agent_v65`/`agent_v67`).

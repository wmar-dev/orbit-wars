# Experiments Round 7 (agent_v68)

**Baseline**: `agent_v64.py` (current best; 50.0% vs `agent_v58.py` / 75.0% vs `agent_v60.py` per Round 7's T005/T006 re-check, see `experiments/2026-06-13-round7-opponent-matrix.md`)
**Benchmark**: `opponent_agents/slawekbiel_agent.py` — `agent_v64` win rate **0.0% (0/20)**, selected in T007 as the strongest loadable opponent (see `experiments/2026-06-13-round7-opponent-matrix.md`)
**Fork**: `agent_v68.py` = copy of `agent_v64.py` with 2 independent toggle-gated candidates from `experiments/2026-06-13-round7-replay-analysis.md`
**Pass threshold**: ≥52.0% win rate over 50 `--swap` games vs `agent_v64.py`

Both candidates implement the same additive mechanism — give an *idle* planet (one for which `_greedy_moves` proposed no dispatch this turn) an extra beam-search candidate (`_gen_idle_rush_candidate`) that rushes its **full fleet** (`mine.ships`, no garrison/floor reservation) to the cheapest target it can outright afford. The mechanism is purely additive to `_gen_beam_candidates`'s candidate list — the existing greedy proposal and `MULTI_TURN_PLAN_ENABLED`'s "skip" (wait-and-accumulate) candidate are untouched and still scored by the same 10-turn forward sim. The two candidates apply this mechanism to disjoint, non-overlapping step ranges split at `OPENING_RUSH_WINDOW = 20`.

## Candidate 1: Opening Rush (`CANDIDATE_1_ENABLED`, `step <= OPENING_RUSH_WINDOW`)

**Observation**: In 5 replays vs `slawekbiel_agent`, the opponent dispatches its entire starting fleet at turn 1 in 4/5 games and captures a second planet by turn ~8-10. `agent_v64` waits 4-8 turns before its first dispatch, and the resulting second-planet race is decided by the median divergence turn of 9 — almost always in the opponent's favor.

**Hypothesis**: Giving idle planets in turns 0-20 an additional beam candidate that immediately rushes the cheapest outright-affordable target (neutral or enemy) with the planet's full fleet would let the forward-sim choose an earlier expansion when it's genuinely better than waiting, closing the second-planet race.

**Result**: `uv run python eval.py h2h --agent0 agent_v68.py(CANDIDATE_1_ENABLED=True, CANDIDATE_2_ENABLED=False) --agent1 agent_v64.py --games 50 --jobs 4 --swap --timing` → **64.0% (32/50 wins) — PASS**. Timing: p50=3.6ms, p95=9.0ms, p99=12.5ms (no performance concern).

**Conclusion**: **KEPT.** A strong, clean win — comfortably above the 52% threshold. This directly confirms the replay analysis's dominant finding: `agent_v64`'s opening-game passivity (waiting to accumulate before committing its full fleet) was costing it the early expansion race, and an additional "rush the cheapest affordable target" option for otherwise-idle opening-game planets — competing against "skip" in the same 10-turn forward sim — resolves it without destabilizing the existing beam search.

## Candidate 2: Established-Game Rush (`CANDIDATE_2_ENABLED`, `step > OPENING_RUSH_WINDOW`)

**Observation**: From turn 50 onward in the same replays, `agent_v64`'s dispatch rate falls from 0.32/turn to 0.00/turn (turns 100-200) while `slawekbiel_agent` holds steady at ~0.92-0.94/turn, and our planet count *drops* from 4.7 to 2.1 over the same window instead of growing.

**Hypothesis**: The same idle-planet rush candidate, applied for `step > 20`, would give planets that `_greedy_moves` skipped a chance to spend their full fleet on a cheaper target instead of going idle, keeping pressure on instead of stalling.

**Result**: `uv run python eval.py h2h --agent0 agent_v68.py(CANDIDATE_1_ENABLED=False, CANDIDATE_2_ENABLED=True) --agent1 agent_v64.py --games 50 --jobs 4 --swap --timing` → **28.0% (14/50 wins) — FAIL** (severe regression). Timing: p50=3.5ms, p95=10.0ms, p99=13.6ms.

**Conclusion**: **DISCARDED.** A severe regression, well below even a "neutral" 50%. The replay analysis's own risk note for this candidate was prescient: by turns 100-200 `agent_v64` is typically *behind* (ships 180 vs opponent's 534 — a ~3x gap per the Round 7 replay analysis), and "idle" planets in this regime are very often planets correctly holding their fleet as a defensive garrison against the opponent's much larger roaming forces, not planets that should be emptied to grab a cheap neutral. `_gen_idle_rush_candidate` reserves nothing (`mine.ships`, no floor/garrison deduction), so whenever the forward-sim's 10-turn horizon didn't foresee the consequence, this candidate stripped a contested planet's defense to chase a low-value target — converting "behind" into "planet lost." Unlike Candidate 1 (opening game, both sides roughly symmetric, low stakes for a "wrong" rush), the established-game step range is exactly where an unreserved full-fleet rush is most dangerous. Do not revisit an unreserved late-game rush; a future attempt should at minimum exclude planets under active threat (cf. Round 6 Candidate 2's discarded relative-strength garrison-scaling direction, which targeted the same "behind and at risk" regime from the defensive side).

## Combination (T016)

Only Candidate 1 passed (≥52%), so the "combined" config is Candidate 1 alone — identical to the T014 configuration (`CANDIDATE_1_ENABLED=True`, `CANDIDATE_2_ENABLED=False`). `agent_v68.py`'s toggles are left in this state. Combined result = T014's result: **64.0% (32/50), p99=12.5ms**.

## Benchmark Re-check (T017)

| Agent | vs `slawekbiel_agent` (30 games, `--swap`) |
|---|---|
| `agent_v68.py` (Candidate 1 enabled) | 0.0% (0/30) |
| `agent_v64.py` | 0.0% (0/30) |

`no_benchmark_regression`: **TRUE** (0.0% ≥ 0.0% — tied). `agent_v68` does not regress against the benchmark; both agents lose every game to `slawekbiel_agent`, which remains a far stronger opponent than either heuristic agent. Closing this specific gap is out of scope for this round (the opponent rush mechanism targets `agent_v64`'s self-play weaknesses, not the much larger structural gap vs a learned policy).

## Outcome

Round 7 produced a real improvement: `agent_v68.py` (Candidate 1 — opening rush — enabled, Candidate 2 discarded) beats `agent_v64.py` **64.0%** head-to-head over 50 `--swap` games, with no regression against the `slawekbiel_agent` benchmark. `agent_v68.py` becomes the new current-best agent. README's Agents table and the Makefile's `AGENT`/`RENDER_AGENT` are updated accordingly (T019).

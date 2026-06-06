# Implementation Plan: Agent Lookahead Decision Search

**Branch**: `021-lookahead-search` | **Date**: 2026-06-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/021-lookahead-search/spec.md`

## Summary

Replace the greedy single-turn dispatch decision in agent_v58 with a budget-driven lookahead search that evaluates multiple candidate action sets extended N turns forward before committing. Three search strategies (beam search, MCTS, N-ply) are implemented in a single unified agent file selectable via a `SEARCH_STRATEGY` constant. The best-performing configuration is submitted to Kaggle. A forward simulator already exists in `agent_v59_beam.py` and will be reused/improved; the core gap to address is weak candidate generation (prior beam search only explored greedy-minus-one-mine subsets, never alternative target assignments).

## Technical Context

**Language/Version**: Python 3 (exact version inherits from Kaggle sandbox; locally via `uv` with `pyproject.toml`)

**Primary Dependencies**: `math`, `time`, `random`, `copy` (stdlib); `kaggle_environments.envs.orbit_wars.orbit_wars.Planet` (game env)

**Storage**: N/A — single-file agent, no disk I/O during play

**Testing**: `make eval` (head-to-head vs `main.py`, 10 games), `make selfplay`, `AGENT=agent_v60.py make eval` for variant evaluation

**Target Platform**: Kaggle sandbox (Python 3, stdlib + `kaggle_environments` only); local: macOS + `.venv` managed by `uv`

**Project Type**: Single-file competition agent (Option A per Principle VI — everything inlined, no local imports)

**Performance Goals**: ≤0.8s per turn (leaving 0.2s margin from the 1-second Kaggle `actTimeout`)

**Constraints**: All helpers inlined (no `from helper import ...`); stdlib + `kaggle_environments` only; no `numpy`, `scipy`, or third-party packages

**Scale/Scope**: Typical game: 20–30 planets, 0–50 in-transit fleets, 500-turn horizon; single agent file ~500–800 lines

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. RL First | **Accepted deviation** | Heuristic lookahead, not RL. Constitution permits "heuristic rule-based logic as a baseline." All prior agents (v2–v58) are heuristic; this continues that lineage. RL path remains open for future work. |
| II. Fair Play | **Pass** | No exploit of engine bugs; `actTimeout` respected via budget-driven search with greedy fallback |
| III. Manual Submissions | **Pass** | Submission gated on local self-play evaluation; submitted manually per workflow |
| IV. Experiment Documentation | **Pass** | Each algorithm variant documented in `experiments/` before Kaggle submission |
| V. Local Self-Play | **Pass** | ≥50 games vs v58 required before submission; depth sensitivity study uses ≥20 games per depth |
| VI. Submission Package | **Pass** | Single self-contained file; all helpers inlined; Principle VI pre-submission check required |
| VII. 95% Confidence | **Pass** | ≥50 game sample provides statistical confidence; multiple algorithm comparison reduces algorithm selection risk |

## Project Structure

### Documentation (this feature)

```text
specs/021-lookahead-search/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
agent_v60.py             # Unified lookahead agent (SEARCH_STRATEGY selectable)
experiments/
└── 2026-06-05-lookahead-search.md   # Experiment log (hypothesis, results, conclusion)
```

---

## Phase 0: Research

### Finding 1 — Why agent_v59_beam underperformed

**Analysis of `agent_v59_beam.py`:**

The beam search in v59_beam generates candidates as subsets of greedy moves:
- Candidate 0: all greedy dispatches as-is
- Candidates 1..N: greedy minus one mine's dispatch (that mine holds)
- Last candidate: hold-all (no dispatches)

**Root flaw**: Candidates only vary *whether* each mine dispatches, never *where* it dispatches. This means the search never explores "mine A attacks target 2 instead of target 1." The candidate space is a binary on/off mask over greedy decisions — it's effectively just asking "should I hold some mines back?" which is a much weaker question than true lookahead.

**Secondary flaw**: The evaluation function scores only production advantage (`own_production - opp_production`) at the horizon. It ignores in-transit ships that arrive before the horizon, which causes the search to undervalue imminent captures.

**Tertiary flaw**: No opponent moves are simulated during rollout — the opponent's planets just accumulate production. This means the rollout is optimistic (we gain planets unchallenged) and diverges from reality, reducing the reliability of the score signal.

**Decision**: Candidate generation must be redesigned to explore alternative target assignments, not just hold/dispatch masks.

---

### Finding 2 — Candidate Generation Redesign

**Approach**: For each owned planet, generate the top-K target candidates by ROI score (not just the single greedy best). An action set is a cross-product sample over per-mine choices.

**Beam search candidate generation** (K=3 targets per mine, M mines):
- Start with greedy assignment (Candidate 0)
- For each mine, generate K-1 alternatives (2nd and 3rd best ROI targets)
- Enumerate combinations: for M mines × K alternatives = K^M total (too many for M>4)
- Pruning: use greedy assignment as the base and vary one mine at a time (O(M×K) candidates), then vary two mines at a time (O(M^2×K^2)) up to budget
- Each candidate = full set of dispatches for that turn, simulated N turns forward

**MCTS** (`random` stdlib only, no numpy):
- Tree nodes represent (GameState, accumulated_score, visit_count)
- Selection: UCB1 = average_score + C × sqrt(ln(parent_visits) / node_visits)
- Expansion: for each mine, sample uniformly from its top-K targets
- Simulation (rollout): apply sampled actions, then simulate N turns with greedy play for both sides
- Backpropagation: update visit counts and average score up the tree
- Budget: run iterations until `time.perf_counter()` exceeds `SEARCH_TIMEOUT`
- Return: action with highest average score (not UCB1) from root's children

**N-ply exhaustive** (depth-limited):
- At each depth level, enumerate all combinations of top-2 targets per mine
- For M=3 mines, depth=3: 2^3 = 8 branches per level → 8^3 = 512 leaves (feasible)
- For M=5 mines: 2^5 = 32 → 32^3 = 32,768 (too slow); prune to vary only 2 mines at once
- Alpha-beta pruning: not applicable (no adversary alternation at our move level), but use beam pruning (keep top-B branches at each level)

**Decision**: Beam search with alternative-target candidates is the recommended starting point (deterministic, easiest to debug). MCTS is second (more exploration power but higher variance). N-ply third (only viable for <4 mines without aggressive pruning).

---

### Finding 3 — Evaluation Function

**Production advantage** (existing):
```
score = sum(p.production for p in planets if p.owner == us)
       - sum(p.production for p in planets if p.owner == them)
```

**Improved: production + in-transit ships** (clarified in spec):
```
score = production_advantage
       + TRANSIT_WEIGHT × sum(f.ships for f in fleets if f.owner == us and f.eta <= horizon)
       - TRANSIT_WEIGHT × sum(f.ships for f in fleets if f.owner == them and f.eta <= horizon)
```

`TRANSIT_WEIGHT` is a tunable constant (initial guess: `0.1`, since 1 production/turn at ETA remaining is worth ~`ETA` ships, so ships ≈ production / max_ETA).

**Note**: Fleets already in `_SimState.fleets` after N steps have either arrived (resolved into planet ownership) or are still in transit. Only still-in-transit own fleets should be counted. The `f.eta` field tracks remaining steps.

---

### Finding 4 — Opponent Modeling

**Greedy opponent model**: During simulation, after applying our action set for turn 1 and then simulating turns 2..N, we need to model the opponent's dispatches each turn. The simplest model: apply the same greedy ROI heuristic for the opponent.

**Implementation complexity**: Calling the full greedy logic for the opponent during each simulation step is expensive (it involves orbit-lead computations). A simplified model: for each opponent planet with surplus ships, dispatch to the nearest non-opponent planet. This is a ~10x speedup vs full greedy and likely sufficient.

**No-opponent variant**: Skip opponent dispatches during simulation; opponent planets just grow. Faster but optimistic.

**Decision**: Start with no-opponent variant for beam/MCTS initial evaluation (fastest). Compare to simplified greedy opponent model as a tuning experiment.

---

### Finding 5 — Depth and Budget

**From v59_beam timing comment**: `baseline 0.29ms/turn; 30 candidates × 5 turns × ~0.03ms = ~4ms overhead`

**Updated timing estimate for redesigned candidates:**
- `_SimState.step()` costs ~0.03ms (measured in v59_beam)
- Candidate generation (generate top-3 targets per mine × 5 mines = 15 alternatives + combinations): ~1ms
- Beam search: 50 candidates × 10 turns × 0.03ms = ~15ms (<<800ms budget)
- MCTS: 500 iterations × 5 turns × 0.03ms = ~75ms (well within budget)
- N-ply at depth 3 with top-2 per mine × 4 mines: 8^3 × 3 turns × 0.03ms = ~590ms (approaching limit)

**Decision**: Start depth study at 5, 10, 15, 20 turns. N-ply depth 3 is the max before risk of timeout.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](data-model.md).

### Unified Agent Architecture

```
agent_v60.py
├── CONSTANTS (including SEARCH_STRATEGY, SEARCH_DEPTH, TRANSIT_WEIGHT, SEARCH_TIMEOUT_MS)
├── _SimPlanet, _SimFleet, _SimState   (reused from v59_beam, score() extended)
├── _build_sim_state()                  (reused from v59_beam)
│
├── _gen_beam_candidates()              (NEW: alternative-target variant generation)
├── _beam_search()                      (REVISED: uses new candidate gen)
│
├── _mcts_search()                      (NEW: UCB1 tree search)
│   └── _mcts_rollout()                 (NEW: greedy rollout from a state)
│
├── _nply_search()                      (NEW: depth-limited exhaustive with beam pruning)
│
├── _lookahead_search()                 (NEW: dispatcher selecting SEARCH_STRATEGY)
│
├── _greedy_moves()                     (extracted from v58 agent() body)
└── agent()                             (thin wrapper: compute greedy → lookahead → return)
```

**Key constant block** (top of file, single place to tune everything):

```python
SEARCH_STRATEGY = "beam"   # "beam" | "mcts" | "nply"
SEARCH_DEPTH    = 10       # turns to simulate forward
TRANSIT_WEIGHT  = 0.1      # weight for in-transit ships in evaluation score
SEARCH_TIMEOUT_MS = 800    # hard wall-clock cutoff in milliseconds
BEAM_K          = 3        # top-K targets per mine for beam candidate generation
MCTS_C          = 1.41     # UCB1 exploration constant (sqrt(2))
NPLY_BEAM_WIDTH = 8        # keep top-N branches at each N-ply level
```

### Key Design Decisions

**Candidate generation for beam search** (revised):
1. Run greedy to get baseline action set (Candidate 0)
2. For each mine, compute top-BEAM_K targets by ROI
3. Generate candidates by varying one mine's target: total = M × (K-1) + 1 candidates (linear, not exponential)
4. Also generate: all-hold, and random combination samples (if budget allows)
5. Simulate each forward SEARCH_DEPTH turns, score with extended evaluation function

**MCTS tree structure**:
- Use a dict-based tree: `{node_id: {score_sum, visit_count, children, action}}`
- Root = current state; children = action sets (one per mine choice sample)
- Each iteration: select via UCB1, expand (new child with sampled action), rollout to depth, backprop

**N-ply**:
- Enumerate top-2 targets per mine
- At each ply, keep only top-NPLY_BEAM_WIDTH branches (beam pruning)
- Return first-turn action of the highest-scoring leaf

**Greedy fallback** (FR-002):
- `greedy_moves` is computed before search begins
- If `time.perf_counter()` exceeds timeout at any point, return `greedy_moves` immediately
- Ensures zero timeout risk

### Evaluation Function Extension

```python
def _score(state, player, horizon):
    prod_adv = (sum(p.production for p in state.planets if p.owner == player)
              - sum(p.production for p in state.planets if 0 <= p.owner != player))
    transit_adv = (sum(f.ships for f in state.fleets if f.owner == player)
                 - sum(f.ships for f in state.fleets if 0 <= f.owner != player))
    return prod_adv + TRANSIT_WEIGHT * transit_adv
```

### Experiment Log Template

Each search strategy variant gets one experiment entry in `experiments/2026-06-05-lookahead-search.md`:

```markdown
## Beam Search (depth=10, K=3)
- **Hypothesis**: Alternative-target beam search outperforms greedy by evaluating 3 targets per mine
- **Change**: agent_v60 with SEARCH_STRATEGY="beam", SEARCH_DEPTH=10, BEAM_K=3
- **Self-play result**: XX% win rate vs v58 over 50 games
- **Conclusion**: [keep/discard/tune]
```

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Principle I (heuristic not RL) | Lookahead is a classical game-search technique; RL training loop is a separate track requiring 1000+ games per experiment | RL-first would require a full training pipeline (PPO/DQN) that takes hours per run; lookahead can be validated in minutes and provides interpretable decision logic |

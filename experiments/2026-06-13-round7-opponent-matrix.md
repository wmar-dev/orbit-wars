# Round 7 Opponent Matrix — 2026-06-13

**Goal**: Select the "Round 7 benchmark opponent" — the loadable opponent against which `agent_v64` has the **lowest** win rate (FR-001/FR-002, [spec.md](../specs/030-experiments-round-7/spec.md)).

## `slawekbiel_agent` / `torch` Unlock Attempt (T002, FR-002)

**Result: SUCCESS** — `uv pip install torch` installed `torch==2.12.0` cleanly on this environment's Python 3.14.0 (cpython-3.14-macos-aarch64 wheel is available; Round 6's assumption that no wheel existed was incorrect/outdated). `opponent_agents/slawekbiel_agent.py` now imports successfully.

`Makefile`'s `install` target updated to include `torch` so this persists for future `make install` runs (local-tooling-only; the agent files themselves remain stdlib + `kaggle_environments`, per Constitution Principle VI — `torch` is never imported by `agent_v64.py`/`agent_v68.py`).

## Opponent Inventory (`opponent_agents/`)

| Opponent | In `KNOWN_OPPONENTS`? | Loadable? | Notes |
|---|---|---|---|
| `sigmaborov` | yes | yes | |
| `dylanxue04` | yes | yes | |
| `yusufmurtaza` | yes | yes | |
| `slawekbiel` | yes | **yes (after torch install)** | Previously unloadable (Round 6); now loads |
| `adilshamim8` | yes | **no** | `SyntaxError: invalid syntax` at line 2 — file is a raw Jupyter cell export (`%%capture` / `!pip install` magics), not valid Python |
| `melccoro` | yes | **no** | Same as above — raw notebook cell export, not valid Python |
| `rahulchauhan016` | yes | **no** | Same as above — raw notebook cell export, not valid Python |
| `hoangson1506` | no | **no** | `ModuleNotFoundError: No module named 'utils'` — incomplete multi-file submission (imports `from utils.registry import register_model`, module not present). Excluded from the sweep. |

## `agent_v64` Win-Rate Sweep (T004-T006)

20 games per opponent (side-alternating via `eval.py opponents`); `agent_v58`/`agent_v60` via 20-game `--swap` h2h.

| Opponent / Sparring Agent | Games | W | D | L | Win% | Tag |
|---|---|---|---|---|---|---|
| sigmaborov | 20 | 20 | 0 | 0 | 100.0% | WIN |
| dylanxue04 | 20 | 20 | 0 | 0 | 100.0% | WIN |
| yusufmurtaza | 20 | 20 | 0 | 0 | 100.0% | WIN |
| slawekbiel | 20 | 0 | 0 | 20 | **0.0%** | **FAIL** |
| adilshamim8 | — | — | — | — | N/A (not loadable) | — |
| melccoro | — | — | — | — | N/A (not loadable) | — |
| rahulchauhan016 | — | — | — | — | N/A (not loadable) | — |
| agent_v58 (sparring) | 20 | 10 | 0 | 10 | 50.0% | EVEN |
| agent_v60 (sparring) | 20 | 15 | 0 | 5 | 75.0% | WIN |

## Benchmark Decision (T007)

**`<BENCHMARK>` = `opponent_agents/slawekbiel_agent.py`**

- `agent_v64` win rate vs `slawekbiel_agent`: **0.0% (0/20)** — `agent_v64` lost every game.
- `is_saturated`: **false** — this is the opposite of saturation; it's the strongest opponent found by a wide margin (next-lowest win rate is 50.0% vs `agent_v58`).
- Verification: ran a single debug game (`seed=42`) directly via `kaggle_environments.make(...).run(['agent_v64.py', 'opponent_agents/slawekbiel_agent.py'])`. Result: Player 0 (`agent_v64`) `reward=-1, status=DONE`; Player 1 (`slawekbiel`) `reward=1, status=DONE`. No exception/crash — this is a genuine, decisive tactical loss, not a loader artifact.
- Rationale: `slawekbiel_agent` is a torch-based ML opponent (previously unloadable in Round 6 due to a missing `torch` wheel for Python 3.14, now resolved — see above). A 0% win rate gives maximal signal for replay-based gap analysis (US2) and a meaningful regression check (T017), in sharp contrast to Round 6's `agent_v58` (already beaten 80%, providing little signal).
- Other findings: `sigmaborov`, `dylanxue04`, `yusufmurtaza` are all fully saturated (100% — `agent_v64` wins every game), consistent with prior rounds. `agent_v60` (75%) is comfortably beaten. `agent_v58` is roughly even (50%), matching T005's earlier Round 7 result.

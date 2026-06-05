# Research: Game Replay Learning

## Decision 1: Replay Storage Format

**Decision**: JSON files, one per game, stored in `replays/` at the project root.

**Rationale**: `kaggle_environments`' `env.run()` returns a Python list of step dicts already structured as JSON-serializable data. Persisting as JSON requires no additional serialization library, keeps files human-readable for manual inspection, and is directly loadable for analysis. Each file is ~1–5 MB for a 500-turn game.

**Alternatives considered**:
- SQLite: overkill for the query patterns needed (sequential scan by game outcome); adds a dependency and makes manual inspection harder.
- Pickle: not human-readable; version-sensitive; no benefit over JSON for this data size.
- CSV: poor fit for nested structures (per-turn planet lists, fleet lists).

---

## Decision 2: What Game State to Capture Per Turn

**Decision**: Capture from the raw `obs` dict that `kaggle_environments` provides to each agent each turn:
- `step` (turn number)
- `planets` list — each entry: `[id, x, y, radius, owner, ships, production]` (all fields in the obs dict)
- `fleets` list — each entry: `[id, owner, ships, source, destination, eta]` (all fields)
- `player` (which player index this obs is from)
- `moves` — the list of actions returned by each agent that turn (captured from the env step output, not from the obs)

**Rationale**: The `env.run()` return value includes both the observation seen by each agent and the action taken. This is sufficient to reconstruct every observable event in the game without accessing agent internals.

**Alternatives considered**: Recording only planet ownership without fleet data loses critical information about in-flight attacks that determine outcomes.

---

## Decision 3: How to Capture Both Agents' Moves

**Decision**: Wrap each agent in a thin recording shim that intercepts the action before it is returned to the environment, appending `(turn, player_idx, moves)` to a shared list. After `env.run()` completes, the move log is merged into the replay.

**Rationale**: `kaggle_environments` does not expose a post-step hook. Wrapping agents is the cleanest interception point. The shim adds no game-affecting logic — it only records and passes through.

**Alternatives considered**: Reconstructing moves from consecutive obs snapshots (inferring which fleets are new) is fragile and error-prone for multi-dispatch turns.

---

## Decision 4: Claude Skill Design

**Decision**: A markdown skill file at `.claude/skills/analyze-replay/SKILL.md` that instructs Claude to:
1. Load replay JSON files from `replays/` (or a specified path/glob)
2. Compute per-turn statistics: planet count delta, ship total delta, dispatches per turn for each agent
3. Identify the "divergence turn" (first turn one agent holds 2× planet count or ship total)
4. Summarize 3+ observable behavioral differences between the agents
5. Propose 1–3 concrete candidate improvements to `agent_v56.py` based purely on observed behavior
6. Write a hypothesis entry to `experiments/YYYY-MM-DD-replay-analysis.md`

**Rationale**: Claude skills in this project are markdown files under `.claude/skills/`. The skill can use the `Bash` and `Read` tools to load replay files, perform Python-based analysis inline, and write the output. This keeps the improvement loop inside the Claude Code session without requiring a separate service.

**Alternatives considered**:
- A standalone `analyze_replays.py` script that calls the Anthropic API: works but breaks the interactive workflow where the developer wants to discuss findings and iterate.
- Hard-coded heuristic analysis: misses the qualitative pattern-recognition that makes Claude useful here.

---

## Decision 5: Replay File Naming and Organization

**Decision**: Files named `replay_{opponent}_{YYYYMMDD_HHMMSS}_{game_index:03d}.json`, stored flat in `replays/`. A `replays/.gitignore` entry excludes them from the repo (can be large).

**Rationale**: Encodes opponent name and timestamp for easy filtering. Sequential index within a batch allows sorting. Flat directory is simpler than per-session subdirectories for 20–50 file batches.

---

## Decision 6: Divergence Turn Definition

**Decision**: First turn `t` where `max(planets_A/planets_B, planets_B/planets_A) >= 2.0` OR `max(ships_A/ships_B, ships_B/ships_A) >= 2.0`, treating 0-planet edge as ratio = infinity (immediate divergence).

**Rationale**: Matches the success criterion in the spec (SC-001). Ratio-based threshold is scale-independent and meaningful at any point in the game.

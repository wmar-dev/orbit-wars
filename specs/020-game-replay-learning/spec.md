# Feature Specification: Game Replay Learning

**Feature Branch**: `020-game-replay-learning`

**Created**: 2026-06-04

**Status**: Draft

**Input**: Learn from looking at games by playing against opponent agents: slawekbiel_agent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Games and Inspect Turn-by-Turn State (Priority: P1)

The developer runs games between agent_v56 and slawekbiel_agent, then browses the recorded game state turn-by-turn to observe what each agent did and how the board evolved — purely from the outside, with no access to the opponent's internals.

**Why this priority**: slawekbiel wins 100% of games vs agent_v56. The developer needs visibility into the game sequence to understand when and how the lead was established, before any improvement can be targeted.

**Independent Test**: Run one game, then browse it turn-by-turn to see planet ownership, ship counts, and fleet moves for both agents at each step.

**Acceptance Scenarios**:

1. **Given** a completed game, **When** the developer steps through the replay, **Then** they can see each planet's owner and ship count for every turn.
2. **Given** a replay, **When** the developer inspects any turn, **Then** they can see which fleet dispatches each agent made that turn (source planet, direction, ships sent).
3. **Given** a replay of a loss, **When** the developer steps through the final 50 turns, **Then** they can identify which planets were lost and at which turns the ship balance shifted decisively.

---

### User Story 2 - Compare Agent Behavior Across a Batch of Games (Priority: P2)

The developer runs 20 games and generates a report comparing both agents' observable behavior: how fast each expands, how aggressively each attacks, and at what point in each game the balance tips.

**Why this priority**: A single game may be noisy. Aggregate patterns across many games reveal systematic differences in strategy that are reliable targets for improvement.

**Independent Test**: Run 20 games, generate a summary, and verify it shows per-turn-bucket statistics (planets owned, ship totals, dispatches) for both agents averaged across all games.

**Acceptance Scenarios**:

1. **Given** 20 completed games, **When** the developer generates a batch summary, **Then** they see average planet count per agent at turn buckets (0–50, 50–100, 100–200, 200+) and the overall win rate.
2. **Given** a batch summary, **When** slawekbiel consistently leads in planet count by a certain turn, **Then** that turn bucket is clearly highlighted as the divergence point.
3. **Given** a batch summary, **When** one agent dispatches significantly more fleets per turn than the other, **Then** the average dispatches-per-turn for each agent is shown.

---

### Edge Cases

- What if an agent errors on a turn? Record game state up to that point and note which turn the error occurred.
- What if a game ends before turn 500 (one player eliminated)? Replay reflects the actual end turn; statistics account for early termination.
- What if the two agents tie? Outcome is recorded as a draw and included in aggregate win-rate calculations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST record complete observable game state (planet owner, ship count, position) for every turn of every game, without accessing agent internals or source code.
- **FR-002**: The system MUST record each agent's fleet dispatches (source planet, angle, ship count) as they appear in the game output each turn.
- **FR-003**: The system MUST save replays to disk so they can be loaded and inspected later without re-running the game.
- **FR-004**: The developer MUST be able to step through a saved replay turn-by-turn and view planet state and fleet moves at each step.
- **FR-005**: The system MUST generate a per-game summary: winner, end turn, final planet counts, final ship totals, total fleet dispatches per agent.
- **FR-006**: The system MUST generate aggregate statistics across a batch of games: win rate, average planet count per agent at turn buckets, average ship total per agent at turn buckets, average dispatches per turn.
- **FR-007**: The system MUST flag, for each game, the first turn at which one agent held a 2× or greater advantage in either planet count or total ships.
- **FR-008**: The developer MUST be able to view a ranked list of replays sorted by how early the decisive lead was established.

### Key Entities

- **Replay**: A complete record of one game — agents, per-turn snapshots, per-turn moves for each agent, outcome (winner, end turn).
- **TurnSnapshot**: Game state at one turn — planet list (id, owner, ships, x, y), in-flight fleets visible in game output.
- **MoveRecord**: One agent's actions for one turn — list of (source\_planet\_id, angle, ships\_sent).
- **BatchSummary**: Aggregated metrics across a set of replays — win rates, per-bucket averages, divergence turn distribution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of recorded losses, the developer can identify the turn at which slawekbiel first achieved a 2× advantage in planets or ships.
- **SC-002**: Aggregate statistics across 20 games are generated in under 30 seconds.
- **SC-003**: After one analysis session, the developer can state at least 3 observable behavioral differences between the two agents (e.g., average planets owned at turn 60, average ships sent per dispatch, average turn of first enemy capture).
- **SC-004**: After one analysis session, the developer produces at least 1 concrete candidate hypothesis for improving agent_v56 based solely on observed game behavior.

## Assumptions

- Learning is black-box: the system observes only what appears in the game output (planet states, fleet moves), never the opponent agent's code or internal variables.
- Replays are stored locally; no remote storage is needed.
- A CLI or script-based interface is sufficient — no graphical game renderer required.
- The kaggle\_environments game output contains enough observable state per turn to reconstruct the full replay.
- The slawekbiel agent is the primary opponent of interest; the system should work with any opponent using the same game interface.

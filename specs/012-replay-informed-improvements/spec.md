# Feature Specification: Replay-Informed Agent Improvements

**Feature Branch**: `012-replay-informed-improvements`

**Created**: 2026-05-31

**Status**: Draft

**Input**: Analysis of replay 78315039 (Isaiah @ Tufa Labs vs 3Comets) to improve agent_v38 (heuristic base) into a new agent_v40

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Production-Weighted Planet Priority (Priority: P1)

As a competitive Kaggle submitter, I want my agent to evaluate and prioritize capturing high-production planets (production ≥ 4) over low-production ones, so it can replicate the decisive resource snowball that won game 78315039.

**Why this priority**: The replay shows the game was decided at step 150 when Isaiah captured 3 additional high-production planets, creating a 78% production rate advantage. This is the single most impactful strategic gap versus the top agent.

**Independent Test**: Run 50 games against agent_v38 and measure whether the agent's planet portfolio skews toward higher-production planets by step 100 (vs a baseline that treats all neutral planets equally).

**Acceptance Scenarios**:

1. **Given** two neutral planets equidistant from a friendly planet — one with production 2, one with production 5 — **When** the agent chooses where to send an expansion fleet, **Then** it targets the production 5 planet at least 75% of the time.
2. **Given** an agent controlling 3 low-production planets with 200 ships available, **When** a high-production (≥4) neutral planet is reachable, **Then** the agent sends at least 60% of available ships to capture it rather than a lower-production alternative.
3. **Given** the agent has replicated Isaiah's pattern of holding 4+ high-production planets by step 150, **When** evaluated over 50 games vs agent_v38, **Then** win rate exceeds 60%.

---

### User Story 2 - Coordinated Multi-Planet Assault (Priority: P2)

As a competitive Kaggle submitter, I want my agent to coordinate attacks from multiple owned planets toward the same target at the same time (synchronized angle), so it overwhelms defenders the way Isaiah overwhelmed 3Comets.

**Why this priority**: Isaiah consistently sent from 2–3 planets at nearly identical angles in the same turn, concentrating firepower. agent_v38's actions per planet are computed independently, missing this coordination.

**Independent Test**: Measure the frequency with which the agent sends from ≥2 planets toward the same approximate destination (within 0.3 radians) in the same turn. Compare baseline (agent_v38) vs improved agent (agent_v40) over 50 games.

**Acceptance Scenarios**:

1. **Given** the agent owns 3+ planets in a cluster, **When** a high-value enemy planet is within range, **Then** the agent dispatches coordinated fleets from at least 2 of those planets in the same turn at least 40% of eligible turns.
2. **Given** coordinated attacks are enabled, **When** the combined fleet from 2 planets exceeds 150% of the defending planet's ships, **Then** the attack succeeds with ≥80% reliability.
3. **Given** 50 test games, **When** comparing coordinated vs uncoordinated attack patterns, **Then** the coordinated variant wins at least 5 percentage points more often.

---

### User Story 3 - Ship-Banking Phase (Priority: P3)

As a competitive Kaggle submitter, I want my agent to recognize when it has a strong production advantage and hold ships rather than immediately spending them, so it can build an overwhelming strike force the way Isaiah did between steps 150–250.

**Why this priority**: Isaiah nearly tripled his ship count (479→1756) in 50 steps by pausing attacks. Premature spending prevents reaching the 1000+ ship mass needed for decisive assaults. Current PPO agent may not learn this "banking" phase naturally.

**Independent Test**: Observe agent behavior in games where it holds a ≥30% production rate advantage. Measure whether total ship count grows for ≥25 consecutive steps before a major offensive (≥500 ships sent in a single turn).

**Acceptance Scenarios**:

1. **Given** the agent controls ≥4 planets with combined production > 25 ships/turn, **When** no enemy planet is directly threatened, **Then** the agent accumulates ships for at least 20 steps before a major offensive at least 50% of the time.
2. **Given** the agent has banked ≥1000 ships, **When** it launches an assault, **Then** it sends ≥800 ships in that turn, capturing at least 2 planets.
3. **Given** a ship-banking strategy, **When** evaluated over 50 games vs agent_v38, **Then** agent_v40's average end-game ship count exceeds agent_v38's average by at least 20%.

---

### Edge Cases

- When both agents target the same high-production neutral planet simultaneously, the agent scales up the fleet size to ensure it arrives with enough ships to capture despite the enemy fleet — it does not abort or retarget.
- When all high-production planets (production ≥ 4) are enemy-owned, two fallback strategies must be implemented and evaluated: (A) treat enemy high-production planets as highest-priority attack targets regardless of cost, and (C) hybrid — attack the least-defended enemy high-production planet while consolidating on available neutrals elsewhere. The best-performing strategy is selected.
- What if coordinated attacks are anticipated by a reactive opponent that reinforces the target before fleets arrive?
- How does ship-banking interact with a fast opponent who expands aggressively during the banking window?
- What if the map has no production ≥4 planets (low-production seed) — does the agent degrade gracefully?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST score each planet using a value function where both production rate and distance are first normalised to [0,1] by the observed map maximum, then combined with production weighted at least 2× more than distance. When an enemy fleet is detected en route to a high-priority neutral planet, the agent MUST scale up its fleet size to win the race rather than abort and retarget.
- **FR-002**: The agent MUST identify the top-N (N ≥ 3) highest-production planets on the map at each decision step. Neutral high-production planets are priority expansion targets. When none remain, two fallback strategies MUST be implemented and evaluated: (A) attack enemy high-production planets directly as the top priority regardless of cost, and (C) hybrid — attack the least-defended enemy high-production planet while also capturing available neutrals. The best-performing strategy is selected for agent_v40.
- **FR-003**: The agent MUST be able to dispatch fleets from multiple owned planets to the same target in the same turn, rather than computing each planet's action independently.
- **FR-004**: The agent MUST implement a "banking mode" that suppresses offensive actions when it holds a production rate advantage. Multiple threshold strategies MUST be implemented and evaluated: (a) fixed threshold (e.g., 800 ships), (b) production-relative threshold (current production rate × N turns), and (c) at least one additional adaptive approach. The best-performing strategy across 50-game eval runs is selected for agent_v40.
- **FR-005**: The agent MUST exit banking mode and launch a coordinated assault when total ships exceeds the banking threshold.
- **FR-006**: The agent MUST maintain compliance with Kaggle actTimeout (≤1 second per turn) — all new logic must be pure numpy/math, no heavy computation.
- **FR-007**: The new agent version MUST comply with Principle VI — either fully self-contained (Option A) or submitted as a multi-file package with all local imports included (Option B).
- **FR-008**: The agent MUST be evaluated against agent_v38 (the current best) over ≥50 games with seed 0 before being designated the new best agent. All variant comparisons (banking threshold strategies, fallback strategies) MUST be recorded in a single combined experiment record at `experiments/012-replay-informed.md` with a results table.

### Key Entities

- **Planet Value Score**: Composite metric per planet. Both production rate and distance are normalised to [0,1] by the observed map maximum before weighting. Production is weighted at least 2× more than distance. Enemy-owned planets are scored separately from neutral ones.
- **Coordinated Attack Group**: A set of ≥2 owned planets that target the same destination in the same turn, computed by grouping planets by proximity to a shared target.
- **Banking Phase**: A game state where the agent withholds offensive fleets to accumulate ships, triggered by production advantage + low ship count conditions.
- **Production Advantage Ratio**: (agent_production_rate) / (opponent_production_rate) — used to gate banking mode and assault timing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The improved agent (agent_v40, based on agent_v38) achieves ≥60% win rate vs agent_v38 over 50 games with seed 0, establishing it as the new best agent.
- **SC-002**: The improved agent demonstrates production-rate advantage (≥25% more ships/turn than opponent) by step 150 in at least 60% of games.
- **SC-003**: The improved agent controls ≥4 high-production planets (production ≥ 4) by step 100 in at least 50% of games where such planets exist.
- **SC-004**: Coordinated multi-planet attacks (≥2 planets targeting the same destination within 0.3 radians, same turn) occur in ≥30% of offensive turns.
- **SC-005**: The improved agent's average end-game ship count (step 499) exceeds agent_v38's average by ≥20% across 50 games.
- **SC-006**: Agent turn time remains under 1 second on the Kaggle sandbox (pure numpy/math inference, no torch dependency).

## Clarifications

### Session 2026-05-31 (continued)

- Q: Should the improved agent implement strategies as rule-based logic on top of an existing agent, or via RL retraining? → A: Rule-based overlay on agent_v38 (the heuristic base agent, not agent_v39 the PPO agent)
- Q: What is agent_v38's win rate vs agent_v39? → A: agent_v38 is better than agent_v39 — agent_v39 (PPO) regressed. agent_v38 is the current best agent.
- Q: Is Kaggle submission of agent_v40 in scope? → A: Out of scope — build and eval only; submission is a separate decision.
- Q: Should the banking threshold be fixed or adaptive? → A: Try different approaches — implement and evaluate multiple threshold strategies (fixed, production-relative, adaptive) and keep the best.
- Q: When all high-production planets are enemy-owned, should the agent attack directly or consolidate first? → A: Try both approaches — (A) attack enemy high-production planets directly as highest-priority targets, and (C) hybrid: attack least-defended enemy high-production planet while consolidating on neutrals. Evaluate both and keep the best.

### Session 2026-05-31 (second pass)

- Q: How should production and distance be normalised in the Planet Value Score? → A: Normalise both to [0,1] by observed map max, then apply weights.
- Q: Should each strategy variant get its own experiment record? → A: Single combined experiment record in experiments/ with a results table comparing all variants.
- Q: When an enemy fleet is already heading toward a high-priority neutral planet, should the agent still send? → A: Send a larger fleet — scale up ships sent to ensure arrival with enough force to still capture.

## Assumptions

- The replay (78315039) is representative of top-tier play — Isaiah @ Tufa Labs is ranked above our current agent on the Kaggle leaderboard, making their strategy a valid north star.
- The base for the improved agent is agent_v38 (the heuristic rule-based agent), not agent_v39 (the PPO RL agent). The three strategies are implemented as deterministic rule-based logic layered on top of agent_v38's existing heuristics.
- Production values per planet are available in `obs.planets[i][6]` (index 6) at each step, as confirmed by the existing observation schema.
- agent_v38 is the current best agent — agent_v39 (PPO RL) regressed relative to it. The target for agent_v40 is to beat agent_v38.
- The improvements can be implemented as a new self-contained agent file (agent_v40.py) that extends agent_v38's logic, following the existing naming convention.
- Ship speed (6.0) and comet speed (4.0) from the analyzed replay match the default Kaggle configuration and apply to all evaluation games.
- No changes to the game engine, reward function, or training infrastructure are required — this spec covers agent logic improvements only.
- Kaggle submission is explicitly out of scope. This feature ends at local evaluation. Submission is a separate decision once eval results are reviewed.
- The eval harness (`eval.py --agent0 --agent1 --games 50 --seed 0`) remains the authoritative benchmark.

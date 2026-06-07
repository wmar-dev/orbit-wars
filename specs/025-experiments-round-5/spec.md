# Feature Specification: Experiments Round 5

**Feature Branch**: `025-experiments-round-5`

**Created**: 2026-06-06

**Status**: Draft

**Input**: User description: "Improve the agent, do as many experiments as necessary"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Multi-Source Coordinated Attack (Priority: P1)

The current beam search generates candidates by replacing ONE planet's dispatch at a time — it swaps the target for a single source planet and simulates. It never evaluates candidates where TWO or more source planets attack the SAME enemy target simultaneously. Coordinated multi-source attacks can break large garrisons that no single source can handle alone, which is critical for eliminating strong opponents. The beam search infrastructure already supports arbitrary candidate generation — this just adds a new candidate type.

**Why this priority**: The slawekbiel opponent likely coordinates multi-source attacks. Our agent never considers this strategy — each planet selects its best individual target independently. Adding multi-source candidates unlocks qualitatively different tactical plans that the current search cannot produce.

**Independent Test**: In `agent_v65.py`, generate additional beam candidates where pairs of nearby sources target the same high-value enemy planet. Run 50-game eval vs v64 (with MULTI_TURN_PLAN_ENABLED on both sides). Target: ≥52% win rate.

**Acceptance Scenarios**:

1. **Given** two nearby allied planets each have surplus ships, **When** an enemy planet with large garrison exists, **Then** at least one beam candidate includes both sources targeting that enemy planet.
2. **Given** multi-source coordination is enabled, **When** running a 50-game eval vs v64, **Then** win rate ≥52%.
3. **Given** multi-source coordination is enabled, **When** the beam search evaluates candidates, **Then** the combined dispatch ships from both sources equals the ships needed to capture the target (no overkill waste).

---

### User Story 2 — Fleet-Size-Optimized Dispatch (Priority: P2)

Currently, `ships_needed = target.ships + 1` for neutral planets and `_enemy_fleet_size()` for enemy planets. Both compute the minimum ships to capture. But fleet speed scales with fleet size: a 100-ship fleet travels ~50% faster than a 10-ship fleet. This means sending slightly MORE ships than the minimum can significantly reduce travel time, which reduces the garrison's production bonus during transit. For distant targets, sending 20% more ships could reduce travel time enough to require fewer total ships overall. This is a pure optimization of the existing dispatch sizing — no new search logic needed.

**Why this priority**: Zero risk — it only changes the `ships_needed` computation in `_greedy_moves` and `_enemy_fleet_size`. The beam search naturally prevents over-dispatch (sending too many ships from one planet hurts score by reducing production elsewhere). If the optimization is correct, it improves efficiency on distant targets.

**Independent Test**: In `agent_v65.py`, modify `ships_needed` computation to optionally oversend for distant targets where the speed bonus reduces travel time enough to offset the extra ships. Run 50-game eval vs v64. Target: ≥52% win rate.

**Acceptance Scenarios**:

1. **Given** a target is very distant (>50 units) and has production >5, **When** computing ships needed, **Then** the agent sends up to 1.5× the minimum to benefit from the fleet speed bonus.
2. **Given** a target is very close (<20 units), **When** computing ships needed, **Then** the agent sends exactly the minimum (no speed benefit worth the extra ships).
3. **Given** fleet-size-optimized dispatch is enabled, **When** running a 50-game eval vs v64, **Then** win rate ≥52%.

---

### User Story 3 — 4-Player State Adaptation (Priority: P3)

The current dispatch logic uses the same aggressiveness regardless of how many opponents remain. In 4-player FFA, being too aggressive leaves planets undefended against 3 potential attackers. In 2-player endgame, being too conservative wastes ships that could eliminate the last opponent. The agent should detect the number of surviving opponents and adjust garrison floor, target selection, and dispatch thresholds accordingly. This directly addresses the Kaggle score discrepancy (v62 dominates 2-player locally but scored low in 4-player evaluation).

**Why this priority**: The Kaggle vs local discrepancy (v62 crushes all opponents in 2-player but scored 792.4 on Kaggle) strongly suggests the agent is poorly tuned for 4-player FFA. This is the experiment most likely to improve Kaggle score.

**Independent Test**: In `agent_v65.py`, adjust garrison floor factor and dispatch thresholds based on number of surviving opponents. Run 50-game eval vs v64. Target: ≥52% win rate. Also run 4-player eval (v65 vs 3 copies of v64) to measure 4-player improvement.

**Acceptance Scenarios**:

1. **Given** 3 opponents are alive, **When** computing garrison floor, **Then** the floor is 1.2× higher than baseline (more conservative defense).
2. **Given** only 1 opponent is alive, **When** computing dispatch thresholds, **Then** the agent attacks the remaining opponent more aggressively (lower garrison floor, no splinter to neutrals).
3. **Given** 4-player adaptation is enabled, **When** running a 4-player eval (v65 vs 3× v64), **Then** v65's average score is higher than v64's in the same position.

---

### Edge Cases

- What happens when multi-source coordination creates candidates where both sources overkill the target (sum of ships >> needed)? The beam search evaluates the score — over-pulling from two planets reduces production at both sources, so the search should naturally prefer efficient allocations.
- What happens when fleet-size optimization oversends for a target that gets captured by another fleet mid-flight? This is a rare edge case — the extra ships become a reinforcement to the captured planet. This is strictly better than undersending (which leaves the garrison intact).
- What happens when 4-player adaptation fires in a 2-player game (e.g., an opponent disconnects)? The opponent count decreases naturally, and the agent transitions from conservative to aggressive. This is the correct behavior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Multi-source coordinated attack candidates MUST evaluate at least one combination of 2+ sources targeting the same enemy planet per game turn.
- **FR-002**: Multi-source coordination MUST be independently togglable via a constant (`MULTI_SOURCE_ENABLED`).
- **FR-003**: Fleet-size-optimized dispatch MUST increase ships_needed by up to 1.5× for distant targets where the fleet speed bonus reduces total travel time.
- **FR-004**: Fleet-size optimization MUST be independently togglable via a constant (`FLEET_SIZE_OPT_ENABLED`).
- **FR-005**: 4-player state adaptation MUST adjust at least the garrison floor factor based on number of surviving opponents.
- **FR-006**: 4-player state adaptation MUST be independently togglable via a constant (`FFA_ADAPT_ENABLED`).
- **FR-007**: `agent_v65.py` MUST be created as a copy of `agent_v64.py`, serving as the experimental platform. `agent_v64.py` remains frozen as the baseline.
- **FR-008**: All experiments MUST be evaluated against v64 using 50-game evals with --swap, recording win rate and per-turn timing (p50/p95/p99).

### Key Entities

- **Multi-source coordinated attack**: Beam search candidates where the disatches/moves list includes entries from 2+ source planets targeting the same target planet ID. Generated by iterating pairs of nearby sources with surplus and finding shared high-ROI targets.
- **Fleet-size optimization**: Modified `_enemy_fleet_size` / ships_needed computation that considers the fleet speed benefit of sending extra ships, computing a "sweet spot" where marginal speed gain per extra ship exceeds the marginal ship cost.
- **4-player state adaptation**: Per-turn computation of surviving opponents (unique planet owners excluding self and neutrals) that adjusts GARRISON_FLOOR_FACTOR, splinter window, and dispatch aggressiveness.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least one of the three experiments achieves ≥52% win rate vs v64 in a 50-game self-play eval with --swap.
- **SC-002**: All experiments complete with p99 per-turn timing < 100ms (12.5% of 800ms budget), confirming no risk of Kaggle timeout.
- **SC-003**: For any experiment that passes, a 4-player eval (vs 3 copies of v64) shows improved average score over v64 in the same position.
- **SC-004**: At least one experiment passes and is included in the combined configuration. The combined config improves over v64's 54% vs v63 baseline.
- **SC-005**: All experiment results are logged in `experiments/2026-06-06-experiments-round5.md` with win rates, sample counts, and conclusions.

## Assumptions

- `agent_v65.py` is created as a copy of v64 serving as the experimental platform. v64 remains frozen as the baseline for all comparisons.
- All experiments are evaluated against v64 (current best, 54% vs v63) as the primary baseline.
- Multi-source coordination uses pair-based candidate generation (2 sources per candidate) rather than full combinatorial (which would explode the candidate count).
- The fleet speed formula (logarithmic scaling from 1 to 6) provides meaningful speed benefit for fleets >50 ships over distances >40 units.
- The 4-player FFA evaluation on Kaggle uses more conservative opponents (not aggressive beam-search agents), which explains v62's score discrepancy — our agent over-attacks and loses to counter-attacks. Higher garrison floors in FFA mode should mitigate this.

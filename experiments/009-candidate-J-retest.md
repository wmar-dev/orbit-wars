# Candidate J Retest — 009-fix-comet-fleet-targeting

**Date**: 2026-05-30

## Hypothesis

Candidate J (smooth adaptive range, 50% score vs v20 — 20 draws) applied a power-law
formula to dynamically scale the range cap `nearest_dist * RANGE_FACTOR`. With the bug-fixed
baseline v32, the mechanic might differentiate vs v32.

## Change vs agent_v32

**INAPPLICABLE.** Candidate J modifies the `nearest_dist * RANGE_FACTOR` range constraint.
However, agent_v30 incorporated Candidate Q (no range limit) which removed this constraint
entirely. Agent_v32 inherits from v31, which inherits from v30 — there is no range cap to
scale. Implementing Candidate J on v32 would mean adding a NEW range constraint back in,
which is a regression of a known improvement (Candidate Q, 70% vs v20).

## Self-Play Result

**No eval run.** Rationale: The mechanic is structurally inapplicable to the v32 baseline
because the constraint it modifies no longer exists. Any test would measure "add a range cap
back" not "improve the existing range mechanic."

## Conclusion

**INAPPLICABLE** — Candidate J is structurally incompatible with v32 (range cap removed in
v30 via Candidate Q). No promotion. Mechanic is permanently superseded by Candidate Q.

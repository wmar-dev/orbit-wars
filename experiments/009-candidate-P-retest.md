# Candidate P Retest — 009-fix-comet-fleet-targeting

**Date**: 2026-05-30
**Hypothesis**: Candidate P (3-iteration orbit lead, 20% vs v20) failed because the
  targeting bug it was trying to fix was still present in v20's base. With the targeting
  bug now properly fixed in agent_v32 (converged fixed-point orbit lead), the 3-iteration
  approach should be subsumed.

## Change vs agent_v32

None — no separate retest file needed. Candidate P's mechanic (extra orbit-lead iterations)
is fully incorporated into agent_v32's `_converged_orbit_lead` function, which iterates
until convergence (delta < 0.1 units) or a cap of 10 iterations. This strictly supersedes
a fixed 3-iteration approach.

## Self-Play Result

**No eval run.** Rationale: Candidate P's entire mechanic is the iterative orbit-lead
refinement, which is now the baseline in agent_v32. A separate test of "3 iterations vs
converged" would have agent_v32_P as a strict subset of agent_v32's fix. Testing it would
measure whether to regress the convergence fix to 3 fixed iterations, which is not the
intent.

## Conclusion

**SUPERSEDED** — Candidate P's orbit-lead improvement is fully incorporated into the
agent_v32 bug fix. The fixed-point convergence (up to 10 iterations) strictly dominates
the 3-iteration approach. No win-rate comparison is warranted.

Next candidate: J (smooth adaptive range).

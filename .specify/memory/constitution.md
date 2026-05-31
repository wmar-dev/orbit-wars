<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Added sections:
  - Principle VI: Self-Contained Agent Files
Modified sections:
  - Development Workflow: added step 0 (self-containment check before submission)
  - Governance: updated Last Amended date
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed (Constitution Check is generic)
  - .specify/templates/spec-template.md ✅ no changes needed
  - .specify/templates/tasks-template.md ✅ no changes needed
Follow-up TODOs: none
Rationale: agent_v38.py was submitted to Kaggle with `from reward_signal import ...`,
  causing ModuleNotFoundError in the Kaggle sandbox. Kaggle receives only the single
  submitted agent file; local modules are not available at runtime. Principle VI
  codifies the self-containment requirement and the pre-submission check to catch
  this class of error before it reaches the leaderboard.
-->

# Orbit Wars Constitution

## Core Principles

### I. Reinforcement Learning First

The agent MUST be trained and improved primarily through reinforcement learning via local
self-play. Heuristic rule-based logic is acceptable as a baseline or opponent seed, but
the primary path to improvement is a learned policy. Training MUST run locally against
self-play opponents — do not rely on online evaluation as the signal for iteration.

### II. Fair Play & Rules Compliance

The agent MUST operate within the official Kaggle Orbit Wars rules at all times. Exploiting
engine bugs, timing loopholes, or undefined behavior is forbidden. The agent MUST respect
the `actTimeout` budget (1 second/turn) and MUST NOT attempt to probe or interfere with
opponent agents outside the game observation. Play to win within the rules, not around them.

### III. Manual Submissions Only

Kaggle submissions MUST be made manually and deliberately. No automated or scripted
submission pipelines are permitted. Before each submission, the submitter MUST confirm
the agent version being submitted and record it in the experiment log. Accidental or
test submissions MUST be noted in the log with a rationale.

### IV. Experiment & Improvement Documentation

Every meaningful training run, architecture change, reward shaping decision, or strategy
hypothesis MUST be documented before or immediately after the experiment. Documentation
MUST include: the hypothesis, the change made, the self-play result (win rate or score
delta), and a conclusion. Undocumented experiments MUST NOT be submitted to Kaggle.

### V. Local Self-Play as the Primary Evaluation Loop

Agent strength MUST be assessed through local self-play before any Kaggle submission.
New agent versions MUST beat (or statistically tie) the previous best local agent in
at least 20 self-play games before being considered for submission. The Kaggle leaderboard
is a lagging signal — local self-play is the ground truth for iteration.

### VI. Self-Contained Agent Files

Every agent file submitted to Kaggle MUST be fully self-contained. The agent file MAY
only import from:

- The Python standard library (e.g., `math`, `random`, `collections`)
- `kaggle_environments` and its sub-packages

Imports from any project-local module (e.g., `reward_signal`, `eval`, or any other `.py`
file in the repository) are FORBIDDEN in agent files. All constants, helper functions,
and logic required by the agent MUST be inlined directly into the agent file before
submission.

**Rationale**: Kaggle's sandbox receives only the single submitted file. Local modules
are absent from the sandbox environment and will raise `ModuleNotFoundError` at runtime,
causing immediate agent failure with no score.

**Pre-submission check**: Before running `make submit`, verify compliance by running:

```bash
grep -n "^from \|^import " agent_vNN.py | grep -v "^.*kaggle_environments\|^.*math\|^.*random\|^.*collections\|^.*itertools\|^.*functools\|^.*heapq\|^.*copy\|^.*typing\|^.*abc\|^.*os\|^.*sys"
```

If the grep returns any output, those imports MUST be inlined before submission.

## Experiment & Documentation Discipline

All experiment records MUST be stored in a `experiments/` directory at the project root.
Each experiment MUST have its own dated file or entry (e.g., `experiments/2026-05-29-ppo-baseline.md`).
Required fields per experiment:

- **Hypothesis**: What improvement is expected and why.
- **Change**: What was modified (model arch, reward, hyperparameters, strategy).
- **Self-play result**: Win rate vs. previous best agent over ≥20 games.
- **Conclusion**: Did it improve? What was learned? Keep or discard?

Submissions to Kaggle MUST reference the experiment entry that validated the submitted agent.

## Development Workflow

0. **Self-containment check**: Before submission, verify the agent file has no imports
   from project-local modules (see Principle VI). Fix any violations by inlining the
   required code into the agent file.
1. Develop and test changes locally using the Makefile (`make test`, `make selfplay`).
2. Document the experiment before or immediately after running self-play evaluation.
3. If self-play shows improvement (≥20 game sample, consistent win rate > 50% vs. prior best),
   tag the agent version and manually submit to Kaggle.
4. Record the submission outcome (leaderboard score, rank delta) back in the experiment log.
5. Never submit directly from a Jupyter notebook without first exporting a clean agent script.

## Governance

This constitution supersedes all other informal practices or undocumented conventions.
Amendments require updating this file with a version bump and a rationale comment.
All implementation plans and task lists MUST include a Constitution Check gate that
verifies compliance with Principles I–VI before proceeding.

- MAJOR bump: Removal or redefinition of a core principle (e.g., dropping RL-first, allowing auto-submit).
- MINOR bump: Addition of a new principle or material expansion of an existing one.
- PATCH bump: Clarifications, wording, or non-semantic refinements.

**Version**: 1.1.0 | **Ratified**: 2026-05-29 | **Last Amended**: 2026-05-30

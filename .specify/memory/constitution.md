<!--
SYNC IMPACT REPORT
==================
Version change: 1.2.0 → 1.3.0
Modified sections: N/A
Added sections:
  - Principle VII: 95% Confidence Decision Gate — new governance principle establishing
    confidence threshold for critical project decisions (submissions, architecture changes,
    reward shaping, methodology shifts).
  - Governance: updated Last Amended date and reflected new principle.
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed
  - .specify/templates/spec-template.md ✅ no changes needed
  - .specify/templates/tasks-template.md ✅ no changes needed
Follow-up TODOs: none
Rationale: Added explicit confidence threshold to formalize decision-making rigor.
  All critical decisions (Kaggle submissions, architecture changes, reward shaping)
  must meet 95% confidence bar before proceeding. Decisions below this threshold must
  be explicitly documented with exception rationale.
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

### VI. Submission Package Completeness

Every Kaggle submission MUST include all files required for the agent to run in the
sandbox. Two valid approaches are permitted:

**Option A — Single self-contained file**: The agent file imports only from the Python
standard library and `kaggle_environments`. All helpers are inlined. No additional files
are submitted.

**Option B — Multi-file package**: The agent file may import from local modules, provided
every required `.py` file is included in the same Kaggle submission package. All submitted
files MUST be listed explicitly before submitting.

Imports from modules that are NOT included in the submission package are FORBIDDEN and
will raise `ModuleNotFoundError` at runtime.

**Rationale**: CONTEST.md confirms multi-file submissions are supported. Option A
(inlining) remains the simplest path for small agents. Option B enables cleaner code
organisation when agent logic grows complex enough to warrant splitting.

**Pre-submission check**: Before running `make submit`, verify every imported local module
is either inlined (Option A) or present in the submission package (Option B):

```bash
# List all local imports in the agent file
grep -n "^from \|^import " agent_vNN.py | grep -v "^.*kaggle_environments\|^.*math\|^.*random\|^.*collections\|^.*itertools\|^.*functools\|^.*heapq\|^.*copy\|^.*typing\|^.*abc\|^.*os\|^.*sys\|^.*numpy\|^.*base64\|^.*pickle"
```

For each result, confirm the module is either inlined or will be submitted alongside
the agent file.

### VII. 95% Confidence Decision Gate

All critical project decisions MUST be made only when there is at least 95% confidence
in the decision. Critical decisions include: Kaggle submissions, major architectural
changes, reward shaping pivots, training methodology shifts, and principle amendments.

Confidence is measured through:
- Rigorous local self-play evaluation (≥20 game baseline for agent decisions)
- Clear experimental hypothesis validation before proceeding
- No outstanding critical unknowns or unaddressed edge cases
- Documentation or peer review confirming alignment with project principles

Decisions made with <95% confidence MUST be explicitly documented with rationale for
the exception and approved by project maintainers before implementation.

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

0. **Submission package check**: Before submission, verify every local import in the agent
   file is either inlined (Option A) or included as a file in the submission package
   (Option B). See Principle VI for the check command.
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

**Version**: 1.3.0 | **Ratified**: 2026-05-29 | **Last Amended**: 2026-05-31

---
name: "analyze-replay"
description: "Analyze one or more game replays vs an opponent agent, surface behavioral patterns and the decisive divergence point, then propose concrete candidate improvements to the current best agent."
argument-hint: "[replay file or glob, e.g. replays/replay_slawekbiel_*.json]"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

## What This Skill Does

1. **Load replays** — find and parse replay JSON files matching the argument (or all files in `replays/` if no argument given)
2. **Compute statistics** — for each game and in aggregate: planet counts per turn bucket, ship totals per turn bucket, dispatches per turn, divergence turn, win/loss breakdown
3. **Identify behavioral differences** — surface at least 3 observable differences between the two agents based purely on game-state data
4. **Pinpoint decisive turns** — identify the median divergence turn across losses and what changed in the 10 turns before it
5. **Propose improvements** — write 1–3 concrete candidate hypotheses for improving the current agent, grounded in the observed patterns
6. **Write experiment entry** — save the analysis to `experiments/YYYY-MM-DD-replay-analysis.md`

## Execution Steps

### Step 1: Locate Replays

If `$ARGUMENTS` is provided, use it as a path or glob pattern relative to the repo root.  
Otherwise, default to all `replays/*.json` files.

List the files that will be analyzed before proceeding.

### Step 2: Parse and Compute Statistics

Run a Python script inline (via Bash tool) to parse the replay files and produce:

```
SUMMARY TABLE
=============
Games analyzed: N
Win rate (our agent): X%

Per-turn-bucket averages (our agent / opponent):
  Turn 0-50:    planets  X.X / Y.Y   ships  XXXX / YYYY   dispatches/turn  X.X / Y.Y
  Turn 50-100:  planets  X.X / Y.Y   ships  XXXX / YYYY   dispatches/turn  X.X / Y.Y
  Turn 100-200: planets  X.X / Y.Y   ships  XXXX / YYYY   dispatches/turn  X.X / Y.Y
  Turn 200+:    planets  X.X / Y.Y   ships  XXXX / YYYY   dispatches/turn  X.X / Y.Y

Divergence turn distribution (losses only):
  Min: N   Median: N   Max: N   (N games with divergence reached)

Per-game outcomes:
  Game 001: LOSS  winner=slawekbiel  end=312  divergence=87   dispatches=[54, 112]
  Game 002: LOSS  winner=slawekbiel  end=498  divergence=103  dispatches=[61, 98]
  ...
```

Use the inline Python script below to parse the replays. Adapt paths as needed:

```python
import json, glob, sys, os
from pathlib import Path

pattern = sys.argv[1] if len(sys.argv) > 1 else "replays/*.json"
files = sorted(glob.glob(pattern))
if not files:
    print(f"No replay files found matching: {pattern}")
    sys.exit(1)

BUCKETS = [(0, 50), (50, 100), (100, 200), (200, 500)]

def bucket_idx(turn):
    for i, (lo, hi) in enumerate(BUCKETS):
        if lo <= turn < hi:
            return i
    return len(BUCKETS) - 1

results = []
for fpath in files:
    with open(fpath) as f:
        r = json.load(f)
    outcome = r["outcome"]
    turns = r["turns"]
    agents = r["agents"]

    bucket_planets = [[[], []] for _ in BUCKETS]
    bucket_ships = [[[], []] for _ in BUCKETS]
    bucket_dispatches = [[[], []] for _ in BUCKETS]

    for t in turns:
        bi = bucket_idx(t["turn"])
        for p in range(2):
            bucket_planets[bi][p].append(t["planet_counts"][p])
            bucket_ships[bi][p].append(t["ship_totals"][p])
            n_dispatches = len(t["moves"][p]["dispatches"])
            bucket_dispatches[bi][p].append(n_dispatches)

    results.append({
        "file": Path(fpath).name,
        "winner": outcome["winner"],
        "end_turn": outcome["end_turn"],
        "divergence_turn": outcome["divergence_turn"],
        "total_dispatches": outcome["total_dispatches"],
        "bucket_planets": bucket_planets,
        "bucket_ships": bucket_ships,
        "bucket_dispatches": bucket_dispatches,
        "agents": agents,
    })

# Aggregate
n = len(results)
wins = sum(1 for r in results if r["winner"] == 0)
print(f"\nSUMMARY TABLE")
print(f"=============")
print(f"Games analyzed: {n}")
print(f"Win rate (our agent): {100*wins/n:.1f}%\n")

bucket_labels = ["Turn 0-50", "Turn 50-100", "Turn 100-200", "Turn 200+"]
print("Per-turn-bucket averages (our agent / opponent):")
for bi, label in enumerate(bucket_labels):
    avgs = []
    for p in range(2):
        all_planets = [v for r in results for v in r["bucket_planets"][bi][p]]
        all_ships = [v for r in results for v in r["bucket_ships"][bi][p]]
        all_disp = [v for r in results for v in r["bucket_dispatches"][bi][p]]
        ap = sum(all_planets)/len(all_planets) if all_planets else 0
        ash = sum(all_ships)/len(all_ships) if all_ships else 0
        ad = sum(all_disp)/len(all_disp) if all_disp else 0
        avgs.append((ap, ash, ad))
    print(f"  {label:<14}: planets {avgs[0][0]:.1f} / {avgs[1][0]:.1f}   "
          f"ships {avgs[0][1]:.0f} / {avgs[1][1]:.0f}   "
          f"dispatches/turn {avgs[0][2]:.2f} / {avgs[1][2]:.2f}")

losses = [r for r in results if r["winner"] != 0]
div_turns = [r["divergence_turn"] for r in losses if r["divergence_turn"] is not None]
print(f"\nDivergence turn distribution (losses only):")
if div_turns:
    div_turns.sort()
    med = div_turns[len(div_turns)//2]
    print(f"  Min: {min(div_turns)}   Median: {med}   Max: {max(div_turns)}   ({len(div_turns)} games)")
else:
    print("  No divergence turns recorded")

print(f"\nPer-game outcomes:")
for r in results:
    w = r["agents"][r["winner"]] if r["winner"] is not None else "draw"
    d = r["total_dispatches"]
    print(f"  {r['file']}: {'WIN' if r['winner']==0 else 'LOSS' if r['winner'] is not None else 'DRAW'}"
          f"  winner={w}  end={r['end_turn']}  divergence={r['divergence_turn']}  dispatches={d}")
```

### Step 3: Identify Behavioral Differences

After reviewing the statistics, identify at least 3 observable behavioral differences. Focus on:

- **Expansion rate**: Which agent controls more planets earlier? At what turn bucket does the gap open?
- **Aggression**: Which agent dispatches more fleets per turn? Does this vary by game phase?
- **Ship efficiency**: Which agent accumulates more total ships relative to planets owned?
- **Divergence pattern**: Is the divergence early (turns 0–100) or late (100+)? Consistent or variable?
- **Endgame behavior**: What does the board look like at the divergence turn? How many planets does each agent hold?

State each difference as a falsifiable observation with numbers, e.g.:  
> "Opponent controls an average of 4.2 planets by turn 50; our agent averages 2.8 — a 50% gap that persists through the game."

### Step 4: Pinpoint What Happens at the Divergence Turn

Look at the 5–10 turns immediately before the median divergence turn in the replay data. Report:
- How many planets does each agent hold at `divergence_turn - 10`?
- What changed between `divergence_turn - 10` and `divergence_turn`? (Planet captured? Large fleet arrived? Our agent failed to dispatch?)

### Step 5: Propose Candidate Improvements

Based **only** on what was observed in the game data (not on knowledge of the opponent's code), propose 1–3 concrete candidate improvements to the current agent. Format each as:

```
Candidate [X]: [Short name]
Observation: [What was seen in the replay data]
Hypothesis: [What change to our agent's behavior might close the gap]
Predicted effect: [How this would change the observable metrics]
Risk: [What could go wrong]
```

Ground each candidate in a specific observed metric (e.g., "opponent dispatches 2.1 fleets/turn in turns 0–50; we dispatch 0.8 — a 2.6× gap").

### Step 6: Write Experiment Entry

Write the findings to `experiments/YYYY-MM-DD-replay-analysis.md` (use today's date). Structure:

```markdown
# Replay Analysis: [Opponent] — [DATE]

**Replays analyzed**: N games
**Win rate**: X%
**Median divergence turn**: N

## Behavioral Differences Observed

1. [Difference 1 with numbers]
2. [Difference 2 with numbers]  
3. [Difference 3 with numbers]

## What Happens at the Divergence Turn

[2–3 sentences describing the board state and what changed]

## Candidate Improvements

### Candidate A: [Name]
**Observation**: ...
**Hypothesis**: ...
**Predicted effect**: ...
**Risk**: ...

### Candidate B: [Name]
...

## Next Step

Run `/speckit-specify` with the most promising candidate to create the next improvement spec.
```

Report the path to the written experiment file as your final output.

## Output Summary

After completing all steps, give a 3–5 sentence summary covering:
- Win rate and median divergence turn
- The most important behavioral difference found
- The top candidate improvement and why it was chosen

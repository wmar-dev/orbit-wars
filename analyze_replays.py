"""Load and analyze Orbit Wars replay files, printing per-turn or batch statistics."""
import argparse
import glob
import json
import os
import sys


# ---------------------------------------------------------------------------
# T015: Turn-by-turn display for a single replay
# ---------------------------------------------------------------------------

def _display_replay(replay):
    """Print a compact turn-by-turn table for a single replay."""
    agents = replay.get("agents", ["us", "opponent"])
    our_name = agents[0] if agents else "us"
    opp_name = agents[1] if len(agents) > 1 else "opponent"
    outcome = replay.get("outcome", {})

    winner = outcome.get("winner")
    result_str = "WIN" if winner == 0 else ("LOSS" if winner == 1 else "DRAW")
    print(f"\nReplay: {our_name} vs {opp_name}  |  Result: {result_str}  |  End turn: {outcome.get('end_turn', '?')}")
    print(f"Divergence turn: {outcome.get('divergence_turn', 'none')}")
    print()

    header = f"{'Turn':>5}  {'OurPlanets':>10}  {'OppPlanets':>10}  {'OurShips':>9}  {'OppShips':>9}  {'OurDisp':>7}  {'OppDisp':>7}"
    print(header)
    print("-" * len(header))

    for rec in replay.get("turns", []):
        pc = rec.get("planet_counts", [0, 0])
        sc = rec.get("ship_totals", [0.0, 0.0])
        moves = rec.get("moves", [{}, {}])
        our_disp = len(moves[0].get("dispatches", [])) if moves else 0
        opp_disp = len(moves[1].get("dispatches", [])) if len(moves) > 1 else 0
        turn = rec.get("turn", 0)
        print(f"{turn:>5}  {pc[0]:>10}  {pc[1]:>10}  {sc[0]:>9.0f}  {sc[1]:>9.0f}  {our_disp:>7}  {opp_disp:>7}")


# ---------------------------------------------------------------------------
# T016: Bucket index + aggregate stats
# ---------------------------------------------------------------------------

def _bucket_index(turn, buckets):
    """Return bucket index for a given turn number."""
    for i in range(len(buckets) - 1):
        if buckets[i] <= turn < buckets[i + 1]:
            return i
    return len(buckets) - 2  # last bucket


def _aggregate_stats(replays, buckets):
    """Compute per-bucket averages for planet counts, ship totals, dispatches."""
    n_buckets = len(buckets) - 1
    # bucket_data[bi][player] = list of per-turn values
    bucket_planets = [[[], []] for _ in range(n_buckets)]
    bucket_ships = [[[], []] for _ in range(n_buckets)]
    bucket_dispatches = [[[], []] for _ in range(n_buckets)]

    for replay in replays:
        for rec in replay.get("turns", []):
            turn = rec.get("turn", 0)
            bi = _bucket_index(turn, buckets)
            pc = rec.get("planet_counts", [0, 0])
            sc = rec.get("ship_totals", [0.0, 0.0])
            moves = rec.get("moves", [{}, {}])
            for p in range(2):
                bucket_planets[bi][p].append(pc[p] if p < len(pc) else 0)
                bucket_ships[bi][p].append(sc[p] if p < len(sc) else 0.0)
                nd = len(moves[p].get("dispatches", [])) if p < len(moves) else 0
                bucket_dispatches[bi][p].append(nd)

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    stats = []
    for bi in range(n_buckets):
        lo, hi = buckets[bi], buckets[bi + 1]
        stats.append({
            "label": f"Turn {lo}-{hi}",
            "our_planets": avg(bucket_planets[bi][0]),
            "opp_planets": avg(bucket_planets[bi][1]),
            "our_ships": avg(bucket_ships[bi][0]),
            "opp_ships": avg(bucket_ships[bi][1]),
            "our_dispatches": avg(bucket_dispatches[bi][0]),
            "opp_dispatches": avg(bucket_dispatches[bi][1]),
        })
    return stats


# ---------------------------------------------------------------------------
# T017: Divergence statistics
# ---------------------------------------------------------------------------

def _divergence_stats(replays):
    """Return min/median/max divergence turn across losses; handles no-divergence games."""
    losses = [r for r in replays if r.get("outcome", {}).get("winner") == 1]
    div_turns = [
        r["outcome"]["divergence_turn"]
        for r in losses
        if r.get("outcome", {}).get("divergence_turn") is not None
    ]
    if not div_turns:
        return {"count": 0, "min": None, "median": None, "max": None, "losses": len(losses)}
    div_turns.sort()
    mid = len(div_turns) // 2
    median = div_turns[mid] if len(div_turns) % 2 == 1 else (div_turns[mid - 1] + div_turns[mid]) // 2
    return {
        "count": len(div_turns),
        "min": div_turns[0],
        "median": median,
        "max": div_turns[-1],
        "losses": len(losses),
    }


# ---------------------------------------------------------------------------
# T018: Print summary
# ---------------------------------------------------------------------------

def _print_summary(agg_stats, div_stats, replays):
    """Print win rate, per-bucket table, divergence distribution, per-game outcomes."""
    n = len(replays)
    wins = sum(1 for r in replays if r.get("outcome", {}).get("winner") == 0)
    draws = sum(1 for r in replays if r.get("outcome", {}).get("winner") is None)
    losses = n - wins - draws

    agents = replays[0].get("agents", ["us", "opponent"]) if replays else ["us", "opponent"]
    our_name = agents[0]
    opp_name = agents[1] if len(agents) > 1 else "opponent"

    print(f"\n{'='*60}")
    print(f"SUMMARY: {our_name} vs {opp_name}")
    print(f"{'='*60}")
    print(f"Games   : {n}   Win: {wins}   Draw: {draws}   Loss: {losses}   Win%: {100*wins/n:.1f}%")
    print()

    print(f"{'Bucket':<16}  {'OurPlanets':>10}  {'OppPlanets':>10}  {'OurShips':>9}  {'OppShips':>9}  {'OurDisp/t':>9}  {'OppDisp/t':>9}")
    print("-" * 82)
    for s in agg_stats:
        print(
            f"{s['label']:<16}  {s['our_planets']:>10.1f}  {s['opp_planets']:>10.1f}  "
            f"{s['our_ships']:>9.0f}  {s['opp_ships']:>9.0f}  "
            f"{s['our_dispatches']:>9.2f}  {s['opp_dispatches']:>9.2f}"
        )
    print()

    print("Divergence turn (losses only):")
    if div_stats["count"] == 0:
        print(f"  No divergence turns recorded across {div_stats['losses']} losses")
    else:
        print(f"  Min: {div_stats['min']}   Median: {div_stats['median']}   Max: {div_stats['max']}   ({div_stats['count']}/{div_stats['losses']} losses reached 2× threshold)")
    print()

    print(f"{'Game':<40}  {'Result':>6}  {'End':>5}  {'Divg':>5}  {'OurDisp':>7}  {'OppDisp':>7}")
    print("-" * 82)
    for r in replays:
        outcome = r.get("outcome", {})
        w = outcome.get("winner")
        result_str = "WIN" if w == 0 else ("LOSS" if w == 1 else "DRAW")
        fname = r.get("_filename", "?")[:38]
        d = outcome.get("total_dispatches", [0, 0])
        print(
            f"{fname:<40}  {result_str:>6}  {outcome.get('end_turn', '?'):>5}  "
            f"{str(outcome.get('divergence_turn', '-')):>5}  {d[0]:>7}  {d[1]:>7}"
        )


# ---------------------------------------------------------------------------
# T019/T020: Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Analyze Orbit Wars replay files.")
    parser.add_argument("--dir", default="replays", help="Directory of replay JSON files (default: replays/)")
    parser.add_argument("--opponent", default=None, help="Filter by opponent slug in filename")
    parser.add_argument("--buckets", default="0,50,100,200,500", help="Turn bucket boundaries, comma-separated (default: 0,50,100,200,500)")
    parser.add_argument("--replay", default=None, help="Path to a single replay file for turn-by-turn display")
    args = parser.parse_args()

    if args.replay:
        # Single replay turn-by-turn display
        try:
            with open(args.replay) as f:
                replay = json.load(f)
            replay["_filename"] = os.path.basename(args.replay)
            _display_replay(replay)
        except Exception as e:
            print(f"Error loading {args.replay}: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # Batch summary mode
    replays = _load_named(args.dir, args.opponent)
    if not replays:
        print("No replays found.")
        sys.exit(0)

    buckets = [int(b.strip()) for b in args.buckets.split(",")]
    if buckets[0] != 0:
        buckets = [0] + buckets
    if buckets[-1] < 500:
        buckets.append(500)

    agg = _aggregate_stats(replays, buckets)
    div = _divergence_stats(replays)
    _print_summary(agg, div, replays)


def _load_named(directory, opponent_slug=None):
    """Load replays and attach filenames for display."""
    pattern = os.path.join(directory, "*.json")
    files = sorted(glob.glob(pattern))
    if opponent_slug:
        files = [f for f in files if opponent_slug in os.path.basename(f)]
    if not files:
        msg = f"No replay files found in {directory}/"
        if opponent_slug:
            msg += f" matching '{opponent_slug}'"
        print(msg)
        return []
    replays = []
    for fpath in files:
        try:
            with open(fpath) as f:
                r = json.load(f)
            if r.get("version") != "1.0":
                continue  # skip non-schema files (e.g. Kaggle episode downloads)
            r["_filename"] = os.path.basename(fpath)
            replays.append(r)
        except Exception as e:
            print(f"  Warning: could not load {fpath}: {e}", file=sys.stderr)
    slug_note = f" (filtered: '{opponent_slug}')" if opponent_slug else ""
    print(f"Loaded {len(replays)} replay{'s' if len(replays) != 1 else ''}{slug_note} from {directory}/")
    return replays


if __name__ == "__main__":
    main()

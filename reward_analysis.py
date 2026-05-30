"""
Orbit Wars - Reward Log Analysis Script

Reads a .jsonl reward log produced by eval.py/eval4.py --reward-log
and prints a Markdown-formatted summary to stdout.

Usage:
    uv run python reward_analysis.py --log rewards.jsonl
    uv run python reward_analysis.py --log rewards.jsonl --games 20
    uv run python reward_analysis.py --log rewards.jsonl --player 0
"""

import argparse
import json
import sys
import time


def load_log(path: str, max_games: int | None, player_filter: int | None) -> dict:
    """Stream-parse .jsonl log into {game_id: [record, ...]}."""
    games: dict[int, list[dict]] = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[reward_analysis] Warning: skipping malformed line: {e}", file=sys.stderr)
                    continue
                gid = rec.get("game_id", 0)
                if max_games is not None and gid >= max_games:
                    continue
                if player_filter is not None and rec.get("player") != player_filter:
                    continue
                games.setdefault(gid, []).append(rec)
    except FileNotFoundError:
        print(f"[reward_analysis] Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    return games


def identify_winners(games: dict) -> dict[int, int | None]:
    """Return {game_id: winner_player} using terminal==max for each game."""
    winners: dict[int, int | None] = {}
    for gid, records in games.items():
        terminal_records = [r for r in records if r.get("terminal") is not None]
        if not terminal_records:
            winners[gid] = None
            continue
        max_terminal = max(r["terminal"] for r in terminal_records)
        tied = [r["player"] for r in terminal_records if r["terminal"] == max_terminal]
        winners[gid] = tied[0] if len(tied) == 1 else None  # None = draw
    return winners


def phase_label(step: int) -> str:
    if step <= 20:
        return "early"
    if step <= 60:
        return "mid"
    return "late"


def avg(values):
    return sum(values) / len(values) if values else 0.0


def print_summary(games: dict, winners: dict, player_filter: int | None):
    components = ["total", "capture_bonus", "production_delta", "ship_delta"]

    # Overall: winner vs loser cumulative reward
    winner_cumulative = []
    loser_cumulative = []
    for gid, records in games.items():
        w = winners.get(gid)
        if w is None:
            continue
        for p_idx in set(r["player"] for r in records):
            player_total = sum(r["total"] for r in records if r["player"] == p_idx)
            if p_idx == w:
                winner_cumulative.append(player_total)
            else:
                loser_cumulative.append(player_total)

    print("## Overall: Winner vs. Loser Cumulative Reward\n")
    print(f"| | Avg cumulative total |")
    print(f"|---|---|")
    print(f"| Winner | {avg(winner_cumulative):.4f} |")
    print(f"| Loser  | {avg(loser_cumulative):.4f} |")
    print()

    # By phase: winner vs loser
    phases = ["early", "mid", "late"]
    print("## By Game Phase (Winner vs. Loser)\n")
    for phase in phases:
        w_data: dict[str, list] = {c: [] for c in components}
        l_data: dict[str, list] = {c: [] for c in components}

        for gid, records in games.items():
            w = winners.get(gid)
            phase_recs = [r for r in records if phase_label(r.get("step", 0)) == phase]
            if not phase_recs:
                continue
            players_in_phase = set(r["player"] for r in phase_recs)
            for p_idx in players_in_phase:
                p_recs = [r for r in phase_recs if r["player"] == p_idx]
                bucket = w_data if p_idx == w else l_data
                for comp in components:
                    bucket[comp].extend(r.get(comp, 0.0) for r in p_recs)

        print(f"### {phase.capitalize()} (turns {'1–20' if phase == 'early' else ('21–60' if phase == 'mid' else '61+')})\n")
        header = "| | " + " | ".join(components) + " |"
        sep = "|---|" + "|".join(["---"] * len(components)) + "|"
        print(header)
        print(sep)
        w_row = "| Winner | " + " | ".join(f"{avg(w_data[c]):.4f}" for c in components) + " |"
        l_row = "| Loser  | " + " | ".join(f"{avg(l_data[c]):.4f}" for c in components) + " |"
        print(w_row)
        print(l_row)
        print()

    # Top-5 high-reward events
    all_records = [r for recs in games.values() for r in recs]
    top5 = sorted(all_records, key=lambda r: r.get("total", 0.0), reverse=True)[:5]
    print("## Top-5 Highest-Reward Events\n")
    print("| game_id | step | player | total | capture_bonus | production_delta | ship_delta |")
    print("|---|---|---|---|---|---|---|")
    for r in top5:
        print(
            f"| {r.get('game_id','?')} | {r.get('step','?')} | {r.get('player','?')} "
            f"| {r.get('total',0):.4f} | {r.get('capture_bonus',0):.4f} "
            f"| {r.get('production_delta',0):.4f} | {r.get('ship_delta',0):.4f} |"
        )
    print()

    # Summary stats
    num_games = len(games)
    draws = sum(1 for w in winners.values() if w is None)
    decided = num_games - draws
    print(f"**Games analysed**: {num_games}  |  **Decided**: {decided}  |  **Draws**: {draws}")
    if player_filter is not None:
        print(f"**Player filter**: player {player_filter}")


def main():
    parser = argparse.ArgumentParser(description="Orbit Wars reward log analyser")
    parser.add_argument("--log", required=True, metavar="PATH", help="Path to .jsonl reward log")
    parser.add_argument("--games", type=int, default=None, metavar="N", help="Limit to first N game IDs")
    parser.add_argument("--player", type=int, default=None, metavar="N", help="Filter to player index N")
    args = parser.parse_args()

    t0 = time.monotonic()
    games = load_log(args.log, args.games, args.player)
    winners = identify_winners(games)

    print(f"# Reward Analysis: {args.log}\n")
    print_summary(games, winners, args.player)

    elapsed = time.monotonic() - t0
    print(f"\n_Analysis completed in {elapsed:.2f}s_")


if __name__ == "__main__":
    main()

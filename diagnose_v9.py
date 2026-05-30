"""
Orbit Wars - Fleet Diagnostic Harness

Runs N games with a given agent, tracks every fleet launch and its outcome,
and writes per-game CSV files to logs/.

Outcome inference (no environment patching):
  - Track fleet list across turns; detect disappearances.
  - When a fleet disappears, check target planet state:
      captured     — target planet changed owner or garrison increased on our side
      transit_loss — target planet unchanged (fleet lost to sun / OOB / intermediate planet)
      unknown      — ambiguous (combat with multiple fleets, etc.)

Usage:
    uv run python diagnose_v9.py [--games N] [--agent PATH] [--seed-start N] [--jobs N]
"""

import argparse
import csv
import importlib.util
import math
import os
from dataclasses import dataclass, fields

from kaggle_environments import make
from kaggle_environments.envs.orbit_wars.orbit_wars import Fleet, Planet


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LaunchRecord:
    game_seed: int
    turn_launched: int
    fleet_id: int
    source_id: int
    target_id: int
    aimed_x: float
    aimed_y: float
    ships: int
    outcome: str        # "captured" | "transit_loss" | "unknown"
    turn_resolved: int


# ---------------------------------------------------------------------------
# Agent loader
# ---------------------------------------------------------------------------

def load_agent(path):
    spec = importlib.util.spec_from_file_location("agent_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


# ---------------------------------------------------------------------------
# Agent wrapper — logs launches and tracks fleets turn-by-turn
# ---------------------------------------------------------------------------

def _find_intended_target(obs, player, angle, source):
    """Return the non-owned planet most aligned with the launch angle."""
    raw_planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
    planets = [Planet(*p) for p in raw_planets]
    best_id = -1
    best_align = -2.0
    for p in planets:
        if p.owner == player:
            continue
        dx = p.x - source.x
        dy = p.y - source.y
        dist = math.hypot(dx, dy)
        if dist < 0.1:
            continue
        align = (dx * math.cos(angle) + dy * math.sin(angle)) / dist
        if align > best_align:
            best_align = align
            best_id = p.id
    return best_id


class DiagnosticWrapper:
    """Wraps an agent to log every fleet launch and track fleet outcomes."""

    def __init__(self, inner_agent, player_id, game_seed):
        self.inner = inner_agent
        self.player_id = player_id
        self.game_seed = game_seed
        self.turn = 0
        # fleet_id -> LaunchRecord (pending resolution)
        self.pending: dict[int, LaunchRecord] = {}
        # fleet_id -> Fleet (last seen)
        self.last_fleets: dict[int, Fleet] = {}
        # planet_id -> Planet (last turn)
        self.last_planets: dict[int, Planet] = {}
        # completed records
        self.records: list[LaunchRecord] = []

    def _planets_map(self, obs):
        raw = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
        return {Planet(*p).id: Planet(*p) for p in raw}

    def _fleets_map(self, obs):
        raw = obs.get("fleets", []) if isinstance(obs, dict) else getattr(obs, "fleets", [])
        return {Fleet(*f).id: Fleet(*f) for f in raw}

    def __call__(self, obs):
        self.turn += 1
        player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
        planets_now = self._planets_map(obs)
        fleets_now = self._fleets_map(obs)

        # Resolve disappeared fleets
        for fid, fleet in self.last_fleets.items():
            if fid not in fleets_now and fid in self.pending:
                rec = self.pending.pop(fid)
                rec.turn_resolved = self.turn
                # Check target planet state vs last turn
                target_then = self.last_planets.get(rec.target_id)
                target_now = planets_now.get(rec.target_id)
                if target_then is None or target_now is None:
                    rec.outcome = "unknown"
                elif target_now.owner == player:
                    rec.outcome = "captured"
                elif target_then.owner != player and target_now.owner != player:
                    # Planet not captured — fleet was lost in transit
                    rec.outcome = "transit_loss"
                else:
                    rec.outcome = "unknown"
                self.records.append(rec)

        # Snapshot planet state before agent acts
        self.last_planets = planets_now

        # Call the real agent
        moves = self.inner(obs)

        # Log new launches
        source_map = {p.id: p for p in planets_now.values() if p.owner == player}
        for move in (moves or []):
            from_id, angle, ships = move
            source = source_map.get(from_id)
            if source is None:
                continue
            target_id = _find_intended_target(obs, player, angle, source)
            target = planets_now.get(target_id)
            aimed_x = target.x if target else float("nan")
            aimed_y = target.y if target else float("nan")

            # Fleet ID will be assigned by the env; use a placeholder keyed by
            # (source, turn) until we can match it in next turn's fleet list.
            rec = LaunchRecord(
                game_seed=self.game_seed,
                turn_launched=self.turn,
                fleet_id=-1,          # resolved on next observation
                source_id=from_id,
                target_id=target_id,
                aimed_x=aimed_x,
                aimed_y=aimed_y,
                ships=ships,
                outcome="pending",
                turn_resolved=-1,
            )
            # Stage as unmatched; match to fleet ID on next call
            self._staged_launches: list[LaunchRecord] = getattr(self, "_staged_launches", [])
            self._staged_launches.append(rec)

        self.last_fleets = fleets_now
        return moves

    def post_turn(self, obs):
        """Call after env processes actions to match staged launches to fleet IDs."""
        if not getattr(self, "_staged_launches", []):
            return
        player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
        fleets_now = self._fleets_map(obs)
        # New fleets are those not in last_fleets
        new_fleet_ids = [fid for fid in fleets_now if fid not in self.last_fleets]
        # Match by source planet id (best effort — order may not be guaranteed)
        staged = getattr(self, "_staged_launches", [])
        for rec in staged:
            matched = False
            for fid in new_fleet_ids:
                f = fleets_now[fid]
                if f.owner == player and f.from_planet_id == rec.source_id and fid not in self.pending:
                    rec.fleet_id = fid
                    self.pending[fid] = rec
                    matched = True
                    break
            if not matched:
                # Can't match — resolve immediately as unknown
                rec.fleet_id = -1
                rec.outcome = "unknown"
                rec.turn_resolved = self.turn
                self.records.append(rec)
        self._staged_launches = []

    def flush_pending(self):
        """Resolve any still-pending fleets at game end as unknown."""
        for fid, rec in self.pending.items():
            rec.outcome = "unknown"
            rec.turn_resolved = self.turn
            self.records.append(rec)
        self.pending.clear()


# ---------------------------------------------------------------------------
# Single-game runner
# ---------------------------------------------------------------------------

def run_game(agent_path, seed):
    """Run one game (self-play), return list of LaunchRecord for player 0."""
    agent_fn = load_agent(agent_path)
    env = make("orbit_wars", configuration={"seed": seed}, debug=False)

    wrapper = DiagnosticWrapper(agent_fn, player_id=0, game_seed=seed)

    env.reset()
    obs_list = env.state

    done = False
    while not done:
        raw_obs_0 = obs_list[0].observation
        raw_obs_1 = obs_list[1].observation

        act0 = wrapper(raw_obs_0)
        act1 = agent_fn(raw_obs_1)   # self-play: same agent as opponent

        env.step([act0, act1])
        obs_list = env.state

        new_obs_0 = obs_list[0].observation
        wrapper.post_turn(new_obs_0)

        done = obs_list[0].status != "ACTIVE"

    wrapper.flush_pending()
    return wrapper.records


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

def write_csv(records: list[LaunchRecord], output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fieldnames = [f.name for f in fields(LaunchRecord)]
    with open(output_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow({f: getattr(rec, f) for f in fieldnames})


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def print_summary(all_records: list[LaunchRecord], agent_path: str):
    total = len(all_records)
    captured = sum(1 for r in all_records if r.outcome == "captured")
    transit = sum(1 for r in all_records if r.outcome == "transit_loss")
    unknown = sum(1 for r in all_records if r.outcome == "unknown")
    transit_pct = (transit / total * 100) if total > 0 else 0.0

    print()
    print(f"--- Diagnostic Summary ({agent_path}) ---")
    print(f"Total launches:   {total}")
    print(f"Captured:         {captured}  ({captured/total*100:.1f}%)" if total else "Captured:         0")
    print(f"Transit loss:     {transit}  ({transit_pct:.1f}%)")
    print(f"Unknown:          {unknown}  ({unknown/total*100:.1f}%)" if total else "Unknown:          0")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Orbit Wars fleet diagnostic harness")
    parser.add_argument("--games", type=int, default=10, help="Number of games to run")
    parser.add_argument("--agent", default="agent_v9.py", help="Path to agent under test")
    parser.add_argument("--seed-start", type=int, default=0, help="Starting random seed")
    parser.add_argument("--jobs", type=int, default=1, help="Parallel worker processes (currently sequential)")
    args = parser.parse_args()

    os.makedirs("logs", exist_ok=True)

    all_records: list[LaunchRecord] = []
    for i in range(args.games):
        seed = args.seed_start + i
        records = run_game(args.agent, seed)
        all_records.extend(records)

        agent_stem = os.path.splitext(os.path.basename(args.agent))[0]
        csv_path = f"logs/diagnose_{agent_stem}_seed{seed}.csv"
        write_csv(records, csv_path)
        print(f"Game {i+1} (seed={seed}): {len(records)} launches logged → {csv_path}")

    print_summary(all_records, args.agent)

    # Write combined CSV
    agent_stem = os.path.splitext(os.path.basename(args.agent))[0]
    combined_path = f"logs/diagnose_{agent_stem}_s{args.seed_start}_{args.games}games.csv"
    write_csv(all_records, combined_path)
    print(f"\nCombined CSV: {combined_path}")


if __name__ == "__main__":
    main()

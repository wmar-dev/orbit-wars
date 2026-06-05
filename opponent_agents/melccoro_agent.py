# Source: melccoro
%%capture
!pip install --upgrade "kaggle-environments>=1.28.0"

import os
import logging

os.environ["KAGGLE_ENVS_LOG_LEVEL"] = "ERROR"
logging.getLogger().setLevel(logging.ERROR)

import random
import numpy as np

random.seed(42)
np.random.seed(42)

from kaggle_environments import make
from kaggle_environments.envs.orbit_wars.orbit_wars import Planet
import matplotlib.pyplot as plt
import math
import pandas as pd
from matplotlib.ticker import MaxNLocator
from tqdm import tqdm

def fleet_speed(num_ships, max_speed=6.0):
    ratio = math.log(num_ships) / math.log(1000)
    ratio = max(0.0, ratio)
    return 1.0 + (max_speed - 1.0) * (ratio ** 1.5)

def split_planets(obs):
    player = obs["player"]
    planets = obs["planets"]

    my_planets = [p for p in planets if p[1] == player]
    targets = [p for p in planets if p[1] != player]

    return my_planets, targets

def get_nearest_target(mine, targets):
    return min(
        targets,
        key=lambda t: math.hypot(mine[2] - t[2], mine[3] - t[3])
    )

def get_angle(source, target):
    dx = target[2] - source[2]
    dy = target[3] - source[3]
    return math.atan2(dy, dx)

def nearest_agent(obs):
    moves = []

    my_planets, targets = split_planets(obs)

    if not my_planets or not targets:
        return moves

    for mine in my_planets:
        nearest = get_nearest_target(mine, targets)

        ships_needed = nearest[5] + 1

        if mine[5] >= ships_needed:
            angle = get_angle(mine, nearest)
            moves.append([mine[0], angle, ships_needed])

    return moves

def print_game_result(env):
    final_obs = env.steps[-1][0].observation
    player = final_obs.player

    all_players = set()
    for step in env.steps:
        obs = step[0].observation
        for p in obs.planets:
            if p[1] != -1:
                all_players.add(p[1])
        for f in obs.fleets:
            if f[1] != -1:
                all_players.add(f[1])

    all_players = sorted(all_players)

    planets = [Planet(*p) for p in final_obs.planets]
    fleets = final_obs.fleets

    scores = {}

    for pid in all_players:
        planet_ships = sum(p.ships for p in planets if p.owner == pid)
        fleet_ships = sum(f[6] for f in fleets if f[1] == pid)
        scores[pid] = planet_ships + fleet_ships

    ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    my_score = scores.get(player, 0)
    my_rank = [pid for pid, _ in ranking].index(player) + 1

    print("===== Game Result =====")
    print(f"My player ID: {player}")
    print(f"My score: {my_score}")
    print(f"My rank: {my_rank} / {len(all_players)}")

    print("Result:", "WIN" if my_rank == 1 else "LOSE")

    print("\nRanking:")
    for rank, (pid, score) in enumerate(ranking, start=1):
        marker = " <-- me" if pid == player else ""
        print(f"{rank}. Player {pid}: {score}{marker}")
        
def plot_game_state(env):
    steps = []

    my_neutral_capture_steps = []
    my_enemy_capture_steps = []
    enemy_neutral_capture_steps = []
    enemy_enemy_capture_steps = []
    lost_planet_steps = []

    prev_owners = None

    players = set()
    for step_idx in range(len(env.steps)):
        obs = env.steps[step_idx][0].observation
        for p in obs.planets:
            if p[1] != -1:
                players.add(p[1])

    players = sorted(players)
    is_multi = len(players) > 2

    for step_idx in range(1, len(env.steps)):
        obs = env.steps[step_idx][0].observation
        player = obs.player
        planets = [Planet(*p) for p in obs.planets]

        curr_owners = {p.id: p.owner for p in planets}

        my_neutral_captures = 0
        my_enemy_captures = 0
        enemy_neutral_captures = 0
        enemy_enemy_captures = 0
        lost_planets = 0

        if prev_owners is not None:
            for pid, curr_owner in curr_owners.items():
                prev_owner = prev_owners.get(pid)

                if prev_owner is None or prev_owner == curr_owner:
                    continue

                if curr_owner == player and prev_owner == -1:
                    my_neutral_captures += 1

                elif curr_owner == player and prev_owner not in (-1, player):
                    my_enemy_captures += 1

                elif prev_owner == player and curr_owner != player:
                    lost_planets += 1

                elif prev_owner == -1 and curr_owner not in (-1, player):
                    enemy_neutral_captures += 1

                elif (
                    prev_owner not in (-1, player)
                    and curr_owner not in (-1, player)
                    and prev_owner != curr_owner
                ):
                    enemy_enemy_captures += 1

        my_neutral_capture_steps.append(my_neutral_captures)
        my_enemy_capture_steps.append(my_enemy_captures)
        enemy_neutral_capture_steps.append(enemy_neutral_captures)
        enemy_enemy_capture_steps.append(enemy_enemy_captures)
        lost_planet_steps.append(lost_planets)

        prev_owners = curr_owners
        steps.append(step_idx)
        
    print_game_result(env)

    # =========================
    # 2-player plot
    # =========================
    if not is_multi:
        my_planets_list = []
        enemy_planets_list = []
        neutral_planets_list = []
        my_ships_list = []
        enemy_ships_list = []

        for step_idx in range(1, len(env.steps)):
            obs = env.steps[step_idx][0].observation
            player = obs.player
            planets = [Planet(*p) for p in obs.planets]

            my_planets = [p for p in planets if p.owner == player]
            enemy_planets = [p for p in planets if p.owner not in (-1, player)]
            neutral_planets = [p for p in planets if p.owner == -1]

            my_planets_list.append(len(my_planets))
            enemy_planets_list.append(len(enemy_planets))
            neutral_planets_list.append(len(neutral_planets))

            my_ships_list.append(sum(p.ships for p in my_planets))
            enemy_ships_list.append(sum(p.ships for p in enemy_planets))

        fig, ax1 = plt.subplots(figsize=(12, 5))

        line1, = ax1.plot(steps, my_planets_list, label="My planets")
        line2, = ax1.plot(steps, enemy_planets_list, label="Enemy planets")
        line3, = ax1.plot(steps, neutral_planets_list, label="Neutral planets")

        ax1.set_xlabel("Step")
        ax1.set_ylabel("Planet count")
        ax1.yaxis.set_major_locator(MaxNLocator(integer=True))

        ax2 = ax1.twinx()
        line4, = ax2.plot(steps, my_ships_list, linestyle="--", label="My ships")
        line5, = ax2.plot(steps, enemy_ships_list, linestyle="--", label="Enemy ships")
        ax2.set_ylabel("Ships")

        ax3 = ax1.twinx()
        ax3.spines["right"].set_position(("outward", 60))

        bars = []
        bottom = [0] * len(steps)

        bar1 = ax3.bar(
            steps,
            my_neutral_capture_steps,
            bottom=bottom,
            alpha=0.35,
            width=1.0,
            label="My neutral captures",
            color="skyblue"
        )
        bars.append(bar1)
        bottom = [b + v for b, v in zip(bottom, my_neutral_capture_steps)]

        bar2 = ax3.bar(
            steps,
            my_enemy_capture_steps,
            bottom=bottom,
            alpha=0.35,
            width=1.0,
            label="My enemy captures",
            color="green"
        )
        bars.append(bar2)
        bottom = [b + v for b, v in zip(bottom, my_enemy_capture_steps)]

        bar3 = ax3.bar(
            steps,
            enemy_neutral_capture_steps,
            bottom=bottom,
            alpha=0.35,
            width=1.0,
            label="Enemy neutral captures",
            color="orange"
        )
        bars.append(bar3)
        bottom = [b + v for b, v in zip(bottom, enemy_neutral_capture_steps)]

        bar4 = ax3.bar(
            steps,
            lost_planet_steps,
            bottom=bottom,
            alpha=0.45,
            width=1.0,
            label="Lost planets",
            color="red"
        )
        bars.append(bar4)

        max_capture = max(
            [
                n + me + en + l
                for n, me, en, l in zip(
                    my_neutral_capture_steps,
                    my_enemy_capture_steps,
                    enemy_neutral_capture_steps,
                    lost_planet_steps
                )
            ],
            default=0
        )

        ax3.set_ylim(0, max_capture + 1)
        ax3.set_ylabel("Capture events")
        ax3.yaxis.set_major_locator(MaxNLocator(integer=True))

        lines = [line1, line2, line3, line4, line5] + bars
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc="upper left")

        plt.title("Game State and Capture Events Over Time")
        plt.show()

    # =========================
    # 4-player plots
    # =========================
    else:
        # 1. Capture Events
        fig, ax = plt.subplots(figsize=(12, 4))

        bottom = [0] * len(steps)

        ax.bar(
            steps,
            my_neutral_capture_steps,
            bottom=bottom,
            color="skyblue",
            alpha=0.4,
            width=1.0,
            label="My neutral captures"
        )
        bottom = [b + v for b, v in zip(bottom, my_neutral_capture_steps)]

        ax.bar(
            steps,
            my_enemy_capture_steps,
            bottom=bottom,
            color="green",
            alpha=0.4,
            width=1.0,
            label="My enemy captures"
        )
        bottom = [b + v for b, v in zip(bottom, my_enemy_capture_steps)]

        ax.bar(
            steps,
            enemy_neutral_capture_steps,
            bottom=bottom,
            color="orange",
            alpha=0.4,
            width=1.0,
            label="Enemy neutral captures"
        )
        bottom = [b + v for b, v in zip(bottom, enemy_neutral_capture_steps)]

        if any(v > 0 for v in enemy_enemy_capture_steps):
            ax.bar(
                steps,
                enemy_enemy_capture_steps,
                bottom=bottom,
                color="purple",
                alpha=0.4,
                width=1.0,
                label="Enemy enemy captures"
            )
            bottom = [b + v for b, v in zip(bottom, enemy_enemy_capture_steps)]

        ax.bar(
            steps,
            lost_planet_steps,
            bottom=bottom,
            color="red",
            alpha=0.5,
            width=1.0,
            label="Lost planets"
        )

        max_capture = max(
            [
                n + me + en + ee + l
                for n, me, en, ee, l in zip(
                    my_neutral_capture_steps,
                    my_enemy_capture_steps,
                    enemy_neutral_capture_steps,
                    enemy_enemy_capture_steps,
                    lost_planet_steps
                )
            ],
            default=0
        )

        ax.set_ylim(0, max_capture + 1)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        ax.set_title("Capture Events Over Time")
        ax.set_xlabel("Step")
        ax.set_ylabel("Capture events")
        ax.legend(loc="upper left")
        plt.show()

        # 2. Planet Count by Player + Neutral
        player_planets = {pid: [] for pid in players}
        neutral_planets_by_step = []

        for step_idx in range(1, len(env.steps)):
            obs = env.steps[step_idx][0].observation
            planets = [Planet(*p) for p in obs.planets]

            neutral_planets_by_step.append(
                len([p for p in planets if p.owner == -1])
            )

            for pid in players:
                owned = [p for p in planets if p.owner == pid]
                player_planets[pid].append(len(owned))

        fig, ax = plt.subplots(figsize=(12, 5))

        for pid in players:
            ax.plot(steps, player_planets[pid], label=f"Player {pid}")

        ax.plot(
            steps,
            neutral_planets_by_step,
            linestyle="--",
            label="Neutral"
        )

        ax.set_title("Planet Count by Player + Neutral")
        ax.set_xlabel("Step")
        ax.set_ylabel("Planet count")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend()
        plt.show()

        # 3. Ship Count by Player
        player_ships = {pid: [] for pid in players}

        for step_idx in range(1, len(env.steps)):
            obs = env.steps[step_idx][0].observation
            planets = [Planet(*p) for p in obs.planets]

            for pid in players:
                owned = [p for p in planets if p.owner == pid]
                player_ships[pid].append(sum(p.ships for p in owned))

        fig, ax = plt.subplots(figsize=(12, 5))

        for pid in players:
            ax.plot(
                steps,
                player_ships[pid],
                linestyle="--",
                label=f"Player {pid}"
            )

        ax.set_title("Ship Count by Player")
        ax.set_xlabel("Step")
        ax.set_ylabel("Ships")
        ax.legend()
        
        plt.show()
    

env = make("orbit_wars", debug=True, configuration={"seed": 42})
env.run([nearest_agent, "random"])
plot_game_state(env)

env = make("orbit_wars", debug=True, configuration={"seed": 42})
env.run([nearest_agent, "random","random","random"])
plot_game_state(env)

def get_reserved_targets(
    obs,
    angle_threshold=0.1,
    use_capture_filter=False
):

    planets = obs["planets"]
    fleets = obs["fleets"]
    player = obs["player"]

    reserved_targets = set()

    # Extract only our fleets
    my_fleets = [f for f in fleets if f[1] == player]

    for f in my_fleets:
        fx, fy = f[2], f[3]      # fleet position
        angle = f[4]             # fleet travel direction

        best_planet = None
        best_angle_diff = float("inf")

        # Try to infer which planet this fleet is heading toward
        for p in planets:

            # Skip origin planet (fleet just launched from here)
            if p[0] == f[5]:
                continue

            dx = p[2] - fx
            dy = p[3] - fy

            # Angle from fleet to this planet
            target_angle = math.atan2(dy, dx)

            # Angle difference normalized to [-pi, pi] (wrap-around safe)
            diff = abs(math.atan2(
                math.sin(target_angle - angle),
                math.cos(target_angle - angle)
            ))

            # Keep the closest match in angle space
            if diff < best_angle_diff:
                best_angle_diff = diff
                best_planet = p

        # If no candidate found, skip
        if best_planet is None:
            continue

        # If angle mismatch is too large, ignore (not likely the target)
        if best_angle_diff >= angle_threshold:
            continue

        # Optional: ignore fleets that cannot actually capture the planet
        if use_capture_filter and f[6] <= best_planet[5]:
            continue

        # Mark this planet as already targeted
        reserved_targets.add(best_planet[0])

    return reserved_targets

def in_flight_agent(obs):
    moves = []

    my_planets, targets = split_planets(obs)
    
    # If nothing to act on, do nothing
    if not my_planets or not targets:
        return moves

    reserved_targets = get_reserved_targets(obs)

    for mine in my_planets:

        # Exclude targets that are already being attacked
        available_targets = [
            t for t in targets if t[0] not in reserved_targets
        ]

        # If no valid targets remain, skip this planet
        if not available_targets:
            continue

        nearest = get_nearest_target(mine, available_targets)

        ships_needed = nearest[5] + 1

        # Only launch if we have enough ships
        if mine[5] >= ships_needed:
            angle = get_angle(mine, nearest)
            # Launch fleet
            moves.append([mine[0], angle, ships_needed])
            reserved_targets.add(nearest[0])

    return moves

env = make("orbit_wars", debug=True, configuration={"seed": 42})
env.run([in_flight_agent, "random"])

plot_game_state(env)

env = make("orbit_wars", debug=True, configuration={"seed": 42})
env.run([in_flight_agent, "random", "random", "random"])

plot_game_state(env)

# Sum ships on owned planets and fleets
def total_ships(obs, player_id):

    planets = obs["planets"]
    fleets = obs["fleets"]

    planet_ships = sum(p[5] for p in planets if p[1] == player_id)
    fleet_ships = sum(f[6] for f in fleets if f[1] == player_id)

    return planet_ships + fleet_ships
    
# Extract per-step game metrics for analysis    
def extract_game_timeseries(env, my_position):
    rows = []
    prev_owners = None

    # Iterate through each game step
    for step_idx in range(1, len(env.steps)):
        obs = env.steps[step_idx][my_position].observation
        player = obs.player
        planets = obs.planets

        # Current owner of each planet
        curr_owners = {p[0]: p[1] for p in planets}

        # Capture event counters for this step
        my_neutral_captures = 0
        my_enemy_captures = 0
        enemy_neutral_captures = 0
        enemy_enemy_captures = 0
        lost_planets = 0

        # Compare current owners with previous step owners
        if prev_owners is not None:
            for planet_id, curr_owner in curr_owners.items():
                prev_owner = prev_owners.get(planet_id)

                # Skip if ownership did not change
                if prev_owner is None or prev_owner == curr_owner:
                    continue

                # I captured a neutral planet
                if curr_owner == player and prev_owner == -1:
                    my_neutral_captures += 1

                # I captured an enemy planet
                elif curr_owner == player and prev_owner not in (-1, player):
                    my_enemy_captures += 1

                # I lost one of my planets
                elif prev_owner == player and curr_owner != player:
                    lost_planets += 1

                # An opponent captured a neutral planet
                elif prev_owner == -1 and curr_owner not in (-1, player):
                    enemy_neutral_captures += 1

                # One opponent captured another opponent's planet
                elif (
                    prev_owner not in (-1, player)
                    and curr_owner not in (-1, player)
                    and prev_owner != curr_owner
                ):
                    enemy_enemy_captures += 1

        # Basic planet counts
        my_planets = [p for p in planets if p[1] == player]
        neutral_planets = [p for p in planets if p[1] == -1]

        ships_by_player = {}
        planet_count_by_player = {}

        # Count ships and planets for each non-neutral player
        for p in planets:
            pid = p[1]
            if pid == -1:
                continue

            ships_by_player[pid] = ships_by_player.get(pid, 0) + p[5]
            planet_count_by_player[pid] = planet_count_by_player.get(pid, 0) + 1

        # Compare against the strongest opponent, not the average opponent
        enemy_players = [pid for pid in ships_by_player if pid != player]

        if enemy_players:
            best_enemy_ships = max(ships_by_player[pid] for pid in enemy_players)
            best_enemy_planets = max(planet_count_by_player[pid] for pid in enemy_players)
        else:
            best_enemy_ships = 0
            best_enemy_planets = 0

        # Store metrics for this step
        rows.append({
            "step": step_idx,

            "my_planets": len(my_planets),
            "best_enemy_planets": best_enemy_planets,
            "neutral_planets": len(neutral_planets),

            "my_ships": sum(p[5] for p in my_planets),
            "best_enemy_ships": best_enemy_ships,

            "my_neutral_captures": my_neutral_captures,
            "my_enemy_captures": my_enemy_captures,
            "enemy_neutral_captures": enemy_neutral_captures,
            "enemy_enemy_captures": enemy_enemy_captures,
            "lost_planets": lost_planets,
        })

        # Save current ownership for next-step comparison
        prev_owners = curr_owners

    return rows
    
# Plot average planets and ships over time (win vs loss)
def plot_average_game_state(timeseries_df):
    for result_label, flag in [("Winning Games", True), ("Losing Games", False)]:
        df_part = timeseries_df[timeseries_df["my_won"] == flag]

        if len(df_part) == 0:
            continue

        avg_df = df_part.groupby("step", as_index=False).mean(numeric_only=True)

        fig, ax1 = plt.subplots(figsize=(12, 5))

        ax1.plot(avg_df["step"], avg_df["my_planets"], label="My planets")
        ax1.plot(avg_df["step"], avg_df["best_enemy_planets"], label="Best opponent")
        ax1.plot(avg_df["step"], avg_df["neutral_planets"], label="Neutral")

        ax1.set_xlabel("Step")
        ax1.set_ylabel("Planet count")

        ax2 = ax1.twinx()
        ax2.plot(avg_df["step"], avg_df["my_ships"], linestyle="--", label="My ships")
        ax2.plot(avg_df["step"], avg_df["best_enemy_ships"], linestyle="--", label="Best opponent ships")

        ax2.set_ylabel("Ships")

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        plt.title(f"Average Game State — {result_label} (Best Opponent)")
        plt.grid(True)
        plt.show()

# Print summary statistics and optionally plot ship margins
def summarize_results(results, plot=True):
    df = pd.DataFrame(results)

    n_games = len(df)

    wins = df["my_won"].sum()
    draws = (df["winner"] == -1).sum()
    losses = n_games - wins - draws

    print("games:", n_games)
    print("wins:", wins)
    print("losses:", losses)
    print("draws:", draws)
    print("win rate:", wins / n_games)
    print("avg rank:", df["my_rank"].mean())
    print("avg total ships:", df["my_total_ships"].mean())
    print("avg best other ships:", df["best_other_ships"].mean())
    print("avg ship margin vs best other:", df["ship_margin_vs_best_other"].mean())
    print("avg final turns:", df["final_turns"].mean())

    if plot:
        plt.figure(figsize=(8, 4))
        plt.bar(range(n_games), df["ship_margin_vs_best_other"])
        plt.axhline(0, linestyle="--")
        plt.xlabel("Game")
        plt.ylabel("Ship margin")
        plt.title("Ship Margin vs Best Opponent")
        plt.grid(True)
        plt.show()

    return df

# Visualize capture events over time (stacked bar)
def plot_average_capture_events(timeseries_df, step_range=None):
    df = timeseries_df.copy()

    if step_range is not None:
        start, end = step_range
        df = df[(df["step"] >= start) & (df["step"] <= end)]

    for result_label, flag in [("Winning Games", True), ("Losing Games", False)]:
        df_part = df[df["my_won"] == flag]

        if len(df_part) == 0:
            print(f"No {result_label.lower()} found.")
            continue

        avg_df = (
            df_part
            .groupby("step", as_index=False)
            .mean(numeric_only=True)
        )

        fig, ax = plt.subplots(figsize=(12, 4))

        bottom = np.zeros(len(avg_df))

        cols = [
            ("my_neutral_captures", "My neutral captures"),
            ("my_enemy_captures", "My enemy captures"),
            ("enemy_neutral_captures", "Enemy neutral captures"),
            ("enemy_enemy_captures", "Enemy enemy captures"),
            ("lost_planets", "Lost planets"),
        ]

        for col, label in cols:
            ax.bar(
                avg_df["step"],
                avg_df[col],
                bottom=bottom,
                alpha=0.4,
                width=1.0,
                label=label
            )
            bottom += avg_df[col].values

        ax.set_title(f"Average Capture Events — {result_label}")
        ax.set_xlabel("Step")
        ax.set_ylabel("Average capture events")
        ax.legend(loc="upper left")
        plt.show()

def evaluate_agents(agents, my_agent, seeds=range(20)):
    results = []
    timeseries_rows = []

    n_players = len(agents)

    if n_players not in [2, 4]:
        raise ValueError("Number of agents must be 2 or 4")

    for seed in seeds:
        lineup = list(agents)
        random.Random(seed).shuffle(lineup)

        my_position = lineup.index(my_agent)

        env = make(
            "orbit_wars",
            debug=False,
            configuration={"seed": seed}
        )
        env.run(lineup)

        final_states = env.steps[-1]
        final_turns = len(env.steps)

        total_ships_list = []

        for player_id in range(n_players):
            obs = final_states[player_id].observation
            total_ships_list.append(total_ships(obs, player_id))

        max_ships = max(total_ships_list)
        winners = [
            player_id
            for player_id, ships in enumerate(total_ships_list)
            if ships == max_ships
        ]

        winner = winners[0] if len(winners) == 1 else -1

        my_total = total_ships_list[my_position]
        best_other = max(
            ships
            for player_id, ships in enumerate(total_ships_list)
            if player_id != my_position
        )

        sorted_ships = sorted(total_ships_list, reverse=True)
        my_rank = sorted_ships.index(my_total) + 1
        my_won = winner == my_position

        result = {
            "seed": seed,
            "my_position": my_position,
            "my_won": my_won,
            "my_rank": my_rank,
            "winner": winner,
            "my_total_ships": my_total,
            "best_other_ships": best_other,
            "ship_margin_vs_best_other": my_total - best_other,
            "final_turns": final_turns,
        }

        for player_id, ships in enumerate(total_ships_list):
            result[f"total_ships_{player_id}"] = ships

        results.append(result)

        game_ts = extract_game_timeseries(env, my_position)

        for row in game_ts:
            row["seed"] = seed
            row["my_won"] = my_won
            row["my_rank"] = my_rank

        timeseries_rows.extend(game_ts)

    return pd.DataFrame(results), pd.DataFrame(timeseries_rows)
    

results_2p, ts_2p = evaluate_agents(
    agents=[in_flight_agent, "random"],
    my_agent=in_flight_agent,
    seeds=range(20)
)

df_2p = summarize_results(results_2p)
plot_average_game_state(ts_2p)
plot_average_capture_events(ts_2p, step_range=(0, 200))

results_4p, ts_4p = evaluate_agents(
    agents=[in_flight_agent, "random", "random", "random"],
    my_agent=in_flight_agent,
    seeds=range(20)
)

df_4p = summarize_results(results_4p, plot=False)
print("\n=== Best Games ===")
display(df_4p.sort_values("ship_margin_vs_best_other", ascending=False).head(5))
print("\n=== Worst Games ===")
display(df_4p.sort_values("ship_margin_vs_best_other").head(5))

plot_average_game_state(ts_4p)
plot_average_capture_events(ts_4p, step_range=(0, 200))

def run_evaluations(agents_dict, seeds=range(10)):
    eval_outputs = {"2p": {}, "4p": {}}

    for name, agent in tqdm(agents_dict.items(), desc="Running ablation"):
        results, ts = evaluate_agents(
            agents=[agent, "random"],
            my_agent=agent,
            seeds=seeds
        )
        eval_outputs["2p"][name] = {"results": results, "timeseries": ts}

        results, ts = evaluate_agents(
            agents=[agent, "random", "random", "random"],
            my_agent=agent,
            seeds=seeds
        )
        eval_outputs["4p"][name] = {"results": results, "timeseries": ts}

    return eval_outputs

def make_ablation_summary(eval_outputs):
    rows = []

    for name, output in eval_outputs.items():
        df = output["results"]

        rows.append({
            "agent": name,
            "games": len(df),
            "win_rate": df["my_won"].mean(),
            "avg_rank": df["my_rank"].mean(),
            "avg_total_ships": df["my_total_ships"].mean(),
            "avg_best_other_ships": df["best_other_ships"].mean(),
            "avg_margin": df["ship_margin_vs_best_other"].mean(),
            "avg_final_turns": df["final_turns"].mean(),
        })

    return pd.DataFrame(rows).sort_values("avg_margin", ascending=False)

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False
):
    def agent(obs):
        moves = []

        step = obs["step"]
        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            nearest = get_nearest_target(mine, available_targets)
            ships_needed = nearest[5] + 1

            if mine[5] >= ships_needed:
                angle = get_angle(mine, nearest)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(nearest[0])

        return moves

    return agent

baseline_in_flight = make_ablation_agent(
    early_off=False,
    angle_threshold=0.1,
    use_capture_filter=False
)

early_off_agent = make_ablation_agent(
    early_off=True,
    angle_threshold=0.1,
    use_capture_filter=False
)

angle_005_agent = make_ablation_agent(
    early_off=False,
    angle_threshold=0.05,
    use_capture_filter=False
)

capture_filter_agent = make_ablation_agent(
    early_off=False,
    angle_threshold=0.1,
    use_capture_filter=True
)

all_adjusted_agent = make_ablation_agent(
    early_off=True,
    angle_threshold=0.05,
    use_capture_filter=True
)

agents = {
    "baseline": baseline_in_flight,
    "early_off": early_off_agent,
    "angle_005": angle_005_agent,
    "capture_filter": capture_filter_agent,
    "all_adjusted": all_adjusted_agent,
}

eval_outputs = run_evaluations(agents, seeds=range(1))

summary_2p = make_ablation_summary(eval_outputs["2p"])
summary_4p = make_ablation_summary(eval_outputs["4p"])

print("=== Ablation Summary (2P) ===")
display(summary_2p)

print("=== Ablation Summary (4P) ===")
display(summary_4p)

early_steps = [0, 25, 50, 75, 100, 150]

early_off_agents = {
    f"early_off_until_{s}": make_ablation_agent(
        early_off=True,
        early_off_until=s,
        angle_threshold=0.1,
        use_capture_filter=False
    )
    for s in early_steps
}

eval_outputs = run_evaluations(early_off_agents, seeds=range(1))

summary_2p = make_ablation_summary(eval_outputs["2p"])
summary_4p = make_ablation_summary(eval_outputs["4p"])

print("=== Early OFF Ablation (2P) ===")
display(summary_2p)

print("=== Early OFF Ablation (4P) ===")
display(summary_4p)

angle_thresholds = [0.03, 0.05, 0.08, 0.1, 0.15, 0.2]

angle_agents = {
    f"angle_{thr}": make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=thr,
        use_capture_filter=False
    )
    for thr in angle_thresholds
}

eval_outputs = run_evaluations(angle_agents, seeds=range(1))

summary_2p = make_ablation_summary(eval_outputs["2p"])
summary_4p = make_ablation_summary(eval_outputs["4p"])

print("=== Angle Threshold Ablation (2P) ===")
display(summary_2p)

print("=== Angle Threshold Ablation (4P) ===")
display(summary_4p)

agents = {
    "early_50_angle_010": make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False
    ),
    "early_50_angle_010_filter": make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=True
    ),
}

eval_outputs = run_evaluations(
    agents,
    seeds=range(1)
)

summary_2p = make_ablation_summary(eval_outputs["2p"])
summary_4p = make_ablation_summary(eval_outputs["4p"])

print("=== Ablation Summary (2P) ===")
display(summary_2p)

print("=== Ablation Summary (4P) ===")
display(summary_4p)

def evaluate_against_baseline(
    variant,
    base,
    seeds=range(1),
    variant_label=None,
    extra_info=None,
    return_outputs=False,
):
    if variant_label is None:
        variant_label = variant.__name__

    if extra_info is None:
        extra_info = {}

    rows = []
    outputs = {}

    for mode in ["2p", "4p"]:
        print(f"\n Running {mode}: {variant_label}")

        if mode == "2p":
            eval_agents = [variant, base]
        else:
            eval_agents = [variant, base, base, base]

        results, ts = evaluate_agents(
            eval_agents,
            my_agent=variant,
            seeds=seeds
        )

        df = summarize_results(results, plot=False)

        rows.append({
            "mode": mode,
            "base_agent": base.__name__,
            "agent": variant_label,
            "win_rate": df["my_won"].mean(),
            "avg_rank": df["my_rank"].mean(),
            "avg_ships": df["my_total_ships"].mean(),
            "ship_margin": df["ship_margin_vs_best_other"].mean(),
            **extra_info,
        })

        outputs[mode] = {
            "results": results,
            "summary_df": df,
            "timeseries": ts,
            "agents": eval_agents,
        }

    if return_outputs:
        return pd.DataFrame(rows), outputs

    return rows

base = agents["early_50_angle_010"]
variant = agents["early_50_angle_010_filter"]


rows = evaluate_against_baseline(
    variant=variant,
    base=base,
    seeds=range(1),
    variant_label=variant.__name__,
)

df = pd.DataFrame(rows)
display(df)

def make_ablation_wrapper(base_agent, move_fn=None, name_suffix="wrapped"):
    def agent(obs):
        moves = base_agent(obs)

        player = obs.get("player", 0) if isinstance(obs, dict) else obs.player
        planets = obs.get("planets", []) if isinstance(obs, dict) else obs.planets
        fleets = obs.get("fleets", []) if isinstance(obs, dict) else obs.fleets
        step = obs.get("step", 0) if isinstance(obs, dict) else getattr(obs, "step", 0)

        planet_by_id = {p[0]: p for p in planets}

        if move_fn is None:
            return moves

        new_moves = []

        for move in moves:
            result = move_fn(
                move=move,
                obs=obs,
                player=player,
                planets=planets,
                fleets=fleets,
                planet_by_id=planet_by_id,
                step=step,
            )

            if result is None:
                continue

            new_moves.append(result)

        return new_moves

    agent.__name__ = f"{base_agent.__name__}_{name_suffix}"
    return agent
    
def avoid_sun_fn_factory(buffer=1.0):
    def move_fn(move, obs, player, planets, fleets, planet_by_id, step):
        from_id, angle, ships = move
        source = planet_by_id.get(from_id)

        if source is None:
            return None

        if path_hits_sun(source, angle, buffer=buffer):
            return None

        return move

    return move_fn
    
def make_avoid_sun_agent(base_agent, buffer=1.0):
    return make_ablation_wrapper(
        base_agent=base_agent,
        move_fn=avoid_sun_fn_factory(buffer=buffer),
        name_suffix=f"avoid_sun_b{buffer}"
    )


def path_hits_sun(source, angle, sun_center=(50.0, 50.0), sun_radius=10.0, buffer=1.0):
    sx, sy = source[2], source[3]
    cx, cy = sun_center

    dx = math.cos(angle)
    dy = math.sin(angle)

    vx = cx - sx
    vy = cy - sy

    t = vx * dx + vy * dy
    if t <= 0:
        return False

    closest_x = sx + t * dx
    closest_y = sy + t * dy

    dist = math.hypot(closest_x - cx, closest_y - cy)

    return dist <= (sun_radius + buffer)

base_agent = agents["early_50_angle_010"]

avoid_sun_agent = make_avoid_sun_agent(
    base_agent=base_agent,
    buffer=1.0
)

avoid_sun_rows = evaluate_against_baseline(
    variant=avoid_sun_agent,
    base=base_agent,
    seeds=range(1),
    variant_label=avoid_sun_agent.__name__,
    extra_info={
        "logic": "avoid_sun",
        "buffer": 1.0,
    }
)

avoid_sun_df = pd.DataFrame(avoid_sun_rows)
avoid_sun_df

buffers = [0.0, 0.5, 1.0, 1.5, 2.0]
results_rows = []

for buffer in tqdm(buffers, desc="Avoid Sun Buffer Ablation"):
    agent = make_avoid_sun_agent(
        base_agent=base_agent,
        buffer=buffer
    )

    rows = evaluate_against_baseline(
        variant=agent,
        base=base_agent, # early_50_angle_0.1
        seeds=range(1),
        variant_label=agent.__name__,
        extra_info={
            "logic": "avoid_sun",
            "buffer": buffer,
        }
    )

    results_rows.extend(rows)

avoid_sun_ablation_df = pd.DataFrame(results_rows)
avoid_sun_ablation_df

def safety_fn_factory(margin=3):
    def move_fn(move, obs, player, planets, fleets, planet_by_id, step):
        from_id, angle, ships = move
        source = planet_by_id.get(from_id)

        if source is None:
            return None

        if source[5] - ships >= margin:
            return move

        return None

    return move_fn
    
def combine_move_fns(*move_fns):
    def combined_fn(move, obs, player, planets, fleets, planet_by_id, step):
        current_move = move

        for fn in move_fns:
            current_move = fn(
                move=current_move,
                obs=obs,
                player=player,
                planets=planets,
                fleets=fleets,
                planet_by_id=planet_by_id,
                step=step,
            )

            if current_move is None:
                return None

        return current_move

    return combined_fn


def make_safety_agent(base_agent, margin=3):
    return make_ablation_wrapper(
        base_agent=base_agent,
        move_fn=safety_fn_factory(margin=margin),
        name_suffix=f"safety_{margin}"
    )

def make_avoid_safety_agent(base_agent, buffer=1.0, margin=3):
    return make_ablation_wrapper(
        base_agent=base_agent,
        move_fn=combine_move_fns(
            avoid_sun_fn_factory(buffer=buffer),
            safety_fn_factory(margin=margin),
        ),
        name_suffix=f"avoid_sun_b{buffer}_safety_{margin}"
    )

margins = [0, 1, 2, 3, 5]
results_rows = []

base_agent =  make_avoid_sun_agent(
        base_agent=agents["early_50_angle_010"],
        buffer=0.5,
    )

for margin in tqdm(margins, desc="Safety on Avoid Sun"):
    variant = make_avoid_safety_agent(
        base_agent=base_agent, # early_50_angle_0.1_sun_0.5
        buffer=0.5,
        margin=margin
    )

    rows = evaluate_against_baseline(
        variant=variant,
        base=base_agent, # early_50_angle_0.1_sun_0.5
        seeds=range(1),
        variant_label=variant.__name__,
        extra_info={
            "logic": "avoid_sun + safety",
            "buffer": 0.5,
            "margin": margin,
        }
    )

    results_rows.extend(rows)

safety_df = pd.DataFrame(results_rows)
safety_df

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,  # NEW: extra margin applied when attacking enemy planets
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]  # NEW: needed to distinguish enemy vs neutral

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            nearest = get_nearest_target(mine, available_targets)

            ships_needed = nearest[5] + 1

            # NEW: apply margin only when attacking enemy-owned planets
            if nearest[1] not in (-1, player):
                ships_needed += enemy_margin

            if mine[5] >= ships_needed:
                angle = get_angle(mine, nearest)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(nearest[0])

        return moves

    return agent

enemy_margins = [0, 1, 2, 3, 5]
results_rows = []

base_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
)

base_agent = make_avoid_sun_agent(
    base_agent=base_core,
    buffer=0.5,
)

for margin in tqdm(enemy_margins, desc="Enemy-only Safety on Avoid Sun"):
    core_variant = make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False,
        enemy_margin=margin,
    )

    variant = make_avoid_sun_agent(
        base_agent=core_variant,
        buffer=0.5,
    )

    rows = evaluate_against_baseline(
        variant=variant,
        base=base_agent,
        seeds=range(1),
        variant_label=variant.__name__,
        extra_info={
            "logic": "avoid_sun + enemy_only_safety",
            "buffer": 0.5,
            "enemy_margin": margin,
        }
    )

    results_rows.extend(rows)

enemy_safety_df = pd.DataFrame(results_rows)
display(enemy_safety_df)

current_base_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
)

base_agent = make_avoid_sun_agent(
    base_agent=current_base_core,
    buffer=0.5,
)

base_agent.__name__ = "early_50_angle_010_safety5_avoid_sun_b0.5"


def estimate_target_defense(source, target, ships_to_send):
    distance = math.hypot(source[2] - target[2], source[3] - target[3])
    speed = fleet_speed(max(1, ships_to_send))
    arrival_turns = distance / speed

    estimated_defense = target[5] + target[6] * arrival_turns

    return math.ceil(estimated_defense)

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
    use_estimate_defense=False,  # NEW: enable future defense estimation
    estimate_scale=1.0,          # NEW: scale estimated defense strength
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            nearest = get_nearest_target(mine, available_targets)

            ships_needed = nearest[5] + 1

            if nearest[1] not in (-1, player):
                ships_needed += enemy_margin

                # NEW: optionally estimate enemy defense at arrival time
                if use_estimate_defense:
                    estimated_defense = estimate_target_defense(
                        source=mine,
                        target=nearest,
                        ships_to_send=ships_needed
                    )

                    # NEW: adjust how conservative the estimate should be
                    scaled_estimate = math.ceil(
                        estimated_defense * estimate_scale
                    )

                    # NEW: send enough ships for the scaled future defense
                    ships_needed = max(
                        ships_needed,
                        scaled_estimate + 1
                    )

            if mine[5] >= ships_needed:
                angle = get_angle(mine, nearest)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(nearest[0])

        return moves

    return agent

estimate_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
)

estimate_agent = make_avoid_sun_agent(
    base_agent=estimate_core,
    buffer=0.5,
)

estimate_agent.__name__ = "early_50_angle_010_safety5_estimate_avoid_sun_b0.5"

rows = evaluate_against_baseline(
    variant=estimate_agent,
    base=base_agent,
    seeds=range(1),
    variant_label=estimate_agent.__name__,
    extra_info={
        "logic": "avoid_sun + enemy_safety + estimate_defense",
        "buffer": 0.5,
        "enemy_margin": 5,
    }
)

estimate_df = pd.DataFrame(rows)
display(estimate_df)

estimate_scales = [0.6, 0.7, 0.8, 0.9, 1.0]
results_rows = []

for scale in tqdm(estimate_scales, desc="Estimate Scale Ablation"):
    estimate_core = make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False,
        enemy_margin=5,
        use_estimate_defense=True,
        estimate_scale=scale,
    )

    estimate_agent = make_avoid_sun_agent(
        base_agent=estimate_core,
        buffer=0.5,
    )

    estimate_agent.__name__ = f"early50_enemy5_est{scale}_avoid_sun_b0.5"

    rows = evaluate_against_baseline(
        variant=estimate_agent,
        base=base_agent,
        seeds=range(1),
        variant_label=estimate_agent.__name__,
        extra_info={
            "logic": "avoid_sun + enemy_safety + scaled_estimate",
            "buffer": 0.5,
            "enemy_margin": 5,
            "estimate_scale": scale,
        }
    )

    results_rows.extend(rows)

estimate_scale_df = pd.DataFrame(results_rows)
display(estimate_scale_df)

base_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
    estimate_scale=0.8,
)

base_agent = make_avoid_sun_agent(
    base_agent=base_core, 
    buffer=0.5,
)

base_agent.__name__ = "early50_angle01_safe5_est08_sun05"

def estimate_enemy_incoming_to_target(
    obs,
    target,
    angle_threshold=0.1
):

    fleets = obs["fleets"]
    player = obs["player"]

    incoming = 0

    for f in fleets:
        # Skip our fleets
        if f[1] == player:
            continue

        fx, fy = f[2], f[3]
        angle = f[4]

        dx = target[2] - fx
        dy = target[3] - fy

        target_angle = math.atan2(dy, dx)

        diff = abs(math.atan2(
            math.sin(target_angle - angle),
            math.cos(target_angle - angle)
        ))

        if diff < angle_threshold:
            incoming += f[6]

    return incoming


def filter_targets_by_enemy_radar(
    obs,
    targets,
    angle_threshold=0.1
):

    filtered_targets = []

    for t in targets:
        # Only apply radar to neutral planets for now
        if t[1] != -1:
            filtered_targets.append(t)
            continue

        enemy_incoming = estimate_enemy_incoming_to_target(
            obs=obs,
            target=t,
            angle_threshold=angle_threshold
        )

        # If enemy can likely capture it, avoid wasting ships
        if enemy_incoming >= t[5] + 1:
            continue

        filtered_targets.append(t)

    return filtered_targets

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
    use_estimate_defense=False,
    estimate_scale=1.0,
    use_enemy_radar=False,        # NEW: enable enemy radar filtering
    radar_angle_threshold=0.1,    # NEW: angle threshold for detecting enemy target direction
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            # NEW: enemy radar v1 filters neutral targets already likely captured by enemies
            if use_enemy_radar:
                available_targets = filter_targets_by_enemy_radar(
                    obs=obs,
                    targets=available_targets,
                    angle_threshold=radar_angle_threshold
                )

                if not available_targets:
                    continue

            nearest = get_nearest_target(mine, available_targets)

            ships_needed = nearest[5] + 1

            # Enemy-owned planet: add fixed safety
            if nearest[1] not in (-1, player):
                ships_needed += enemy_margin

                # Optional estimate defense at arrival
                if use_estimate_defense:
                    estimated_defense = estimate_target_defense(
                        source=mine,
                        target=nearest,
                        ships_to_send=ships_needed
                    )

                    scaled_estimate = math.ceil(
                        estimated_defense * estimate_scale
                    )

                    ships_needed = max(
                        ships_needed,
                        scaled_estimate + 1
                    )

            if mine[5] >= ships_needed:
                angle = get_angle(mine, nearest)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(nearest[0])

        return moves

    return agent

radar_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
    estimate_scale=0.8,
    use_enemy_radar=True,
    radar_angle_threshold=0.1,
)

radar_agent = make_avoid_sun_agent(
    base_agent=radar_core,
    buffer=0.5,
)

radar_agent.__name__ = "early50_angle01_safe5_est08_sun05_radar"

rows = evaluate_against_baseline(
    variant=radar_agent,
    base=base_agent,
    seeds=range(1),
    variant_label=radar_agent.__name__,
    extra_info={
        "logic": "avoid_sun + enemy_safety + estimate + enemy_radar",
        "buffer": 0.5,
        "enemy_margin": 5,
        "estimate_scale": 0.8,
        "radar_angle_threshold": 0.1,
    }
)

radar_df = pd.DataFrame(rows)
display(radar_df)

base_results_2p, base_ts_2p = evaluate_agents(
    agents=[base_agent, "random"],
    my_agent=base_agent,
    seeds=range(1)
)

radar_results_2p, radar_ts_2p = evaluate_agents(
    agents=[radar_agent, "random"],
    my_agent=radar_agent,
    seeds=range(1)
)

df_2p = summarize_results(base_results_2p)
df_2p = summarize_results(radar_results_2p)

base_results_4p, base_ts_4p = evaluate_agents(
    agents=[base_agent, "random", "random", "random"],
    my_agent=base_agent,
    seeds=range(1)
)

radar_results_4p, radar_ts_4p = evaluate_agents(
    agents=[radar_agent, "random", "random", "random"],
    my_agent=radar_agent,
    seeds=range(1)
)

df_4p = summarize_results(base_results_4p)
df_4p = summarize_results(radar_results_4p)

radar_thresholds = [0.03, 0.05, 0.08, 0.1, 0.15, 0.2]
results_rows = []

for th in tqdm(radar_thresholds, desc="Radar Angle Threshold Ablation"):
    radar_core = make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False,
        enemy_margin=5,
        use_estimate_defense=True,
        estimate_scale=0.8,
        use_enemy_radar=True,
        radar_angle_threshold=th,
    )

    radar_agent = make_avoid_sun_agent(
        base_agent=radar_core,
        buffer=0.5,
    )

    radar_agent.__name__ = f"early50_safe5_est08_radar{th}_sun05"

    rows = evaluate_against_baseline(
        variant=radar_agent,
        base=base_agent,
        seeds=range(1),
        variant_label=radar_agent.__name__,
        extra_info={
            "logic": "avoid_sun + enemy_safety + estimate + radar",
            "buffer": 0.5,
            "enemy_margin": 5,
            "estimate_scale": 0.8,
            "radar_angle_threshold": th,
        }
    )

    results_rows.extend(rows)

radar_threshold_df = pd.DataFrame(results_rows)
display(radar_threshold_df)

radar_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
    estimate_scale=0.8,
    use_enemy_radar=True,
    radar_angle_threshold=0.15
)

radar_agent = make_avoid_sun_agent(
    base_agent=radar_core,
    buffer=0.5,
)

radar_agent.__name__ = "early50_angle01_safe5_est08_radar015_sun05"

base_agent = radar_agent

def get_comet_ids(obs):
    return set(obs.get("comet_planet_ids", []))


def get_comet_remaining_steps(obs, comet_id, default=999):
    for group in obs.get("comets", []):
        planet_ids = group.get("planet_ids", [])
        if comet_id not in planet_ids:
            continue

        idx = planet_ids.index(comet_id)
        paths = group.get("paths", [])
        path_index = group.get("path_index", 0)

        if idx >= len(paths):
            return default

        return len(paths[idx]) - path_index - 1

    return default


def get_nearest_owned_non_comet(source, my_planets, comet_ids):
    candidates = [
        p for p in my_planets
        if p[0] != source[0] and p[0] not in comet_ids
    ]

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda p: math.hypot(source[2] - p[2], source[3] - p[3])
    )


def get_best_comet_target(
    mine,
    available_targets,
    obs,
    comet_ids,
    max_comet_ships=30,
    max_comet_distance=35,
    min_remaining_steps=25,
):

    candidates = []

    for t in available_targets:
        if t[0] not in comet_ids:
            continue

        ships_needed = t[5] + 1
        distance = math.hypot(mine[2] - t[2], mine[3] - t[3])
        remaining = get_comet_remaining_steps(obs, t[0])

        if ships_needed > max_comet_ships:
            continue

        if distance > max_comet_distance:
            continue

        if remaining < min_remaining_steps:
            continue

        if mine[5] < ships_needed:
            continue

        candidates.append(t)

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda t: (
            math.hypot(mine[2] - t[2], mine[3] - t[3]),
            t[5]
        )
    )

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
    use_estimate_defense=False,
    estimate_scale=1.0,
    use_enemy_radar=False,
    radar_angle_threshold=0.1,
    use_comets=False,              # NEW: enable comet-specific logic
    comet_evac_remaining=12,       # NEW: threshold for evacuating comet planets
    max_comet_ships=30,            # NEW: max ships to invest in comet capture
    max_comet_distance=35,         # NEW: max distance to consider comet targets
    min_comet_remaining=25,        # NEW: minimum remaining lifetime for comet
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        comet_ids = get_comet_ids(obs)   # NEW: identify active comet planets
        evacuated_sources = set()        # NEW: track comet planets already evacuated

        # NEW: (1) Evacuate owned comets before they disappear
        if use_comets:
            for comet in my_planets:
                if comet[0] not in comet_ids:
                    continue

                remaining = get_comet_remaining_steps(obs, comet[0])

                if remaining > comet_evac_remaining:
                    continue

                destination = get_nearest_owned_non_comet(
                    source=comet,
                    my_planets=my_planets,
                    comet_ids=comet_ids
                )

                if destination is None:
                    continue

                ships_to_send = comet[5]

                if ships_to_send <= 0:
                    continue

                angle = get_angle(comet, destination)
                moves.append([comet[0], angle, ships_to_send])
                evacuated_sources.add(comet[0])

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            if mine[0] in evacuated_sources:  # NEW: skip already evacuated comet sources
                continue

            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            if use_enemy_radar:
                available_targets = filter_targets_by_enemy_radar(
                    obs=obs,
                    targets=available_targets,
                    angle_threshold=radar_angle_threshold
                )

                if not available_targets:
                    continue

            # NEW: (2) Prefer nearby, safe comet targets if conditions are met
            if use_comets:
                comet_target = get_best_comet_target(
                    mine=mine,
                    available_targets=available_targets,
                    obs=obs,
                    comet_ids=comet_ids,
                    max_comet_ships=max_comet_ships,
                    max_comet_distance=max_comet_distance,
                    min_remaining_steps=min_comet_remaining,
                )

                if comet_target is not None:
                    nearest = comet_target
                else:
                    nearest = get_nearest_target(mine, available_targets)
            else:
                nearest = get_nearest_target(mine, available_targets)

            ships_needed = nearest[5] + 1

            if nearest[1] not in (-1, player):
                ships_needed += enemy_margin

                if use_estimate_defense:
                    estimated_defense = estimate_target_defense(
                        source=mine,
                        target=nearest,
                        ships_to_send=ships_needed
                    )

                    scaled_estimate = math.ceil(
                        estimated_defense * estimate_scale
                    )

                    ships_needed = max(
                        ships_needed,
                        scaled_estimate + 1
                    )

            if mine[5] >= ships_needed:
                angle = get_angle(mine, nearest)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(nearest[0])

        return moves

    return agent

comet_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
    estimate_scale=0.8,
    use_enemy_radar=True,
    radar_angle_threshold=0.1,
    use_comets=True,
    comet_evac_remaining=12,
    max_comet_ships=30,
    max_comet_distance=35,
    min_comet_remaining=25,
)

comet_agent = make_avoid_sun_agent(
    base_agent=comet_core,
    buffer=0.5,
)

comet_agent.__name__ = "early50_angle01_safe5_est08_radar_comet_sun05"

rows = evaluate_against_baseline(
    variant=comet_agent,
    base=base_agent,
    seeds=range(1),
    variant_label=comet_agent.__name__,
    extra_info={
        "logic": "avoid_sun + enemy_safety + estimate + radar + comet",
        "buffer": 0.5,
        "enemy_margin": 5,
        "estimate_scale": 0.8,
        "comet_evac_remaining": 12,
        "max_comet_ships": 30,
        "max_comet_distance": 35,
        "min_comet_remaining": 25,
    }
)

comet_df = pd.DataFrame(rows)
display(comet_df)

def get_best_comet_target_v2(
    mine,
    available_targets,
    obs,
    comet_ids,
    max_comet_ships=12,
    max_comet_distance=22,
    min_remaining_steps=30,
    max_source_production=2,
):
    # Only use low-production planets for comet capture
    if mine[6] > max_source_production:
        return None

    candidates = []

    for t in available_targets:
        if t[0] not in comet_ids:
            continue

        ships_needed = t[5] + 1
        distance = math.hypot(mine[2] - t[2], mine[3] - t[3])
        remaining = get_comet_remaining_steps(obs, t[0])

        if ships_needed > max_comet_ships:
            continue
        if distance > max_comet_distance:
            continue
        if remaining < min_remaining_steps:
            continue
        if mine[5] < ships_needed:
            continue

        candidates.append(t)

    if not candidates:
        return None

    return min(
        candidates,
        key=lambda t: (
            math.hypot(mine[2] - t[2], mine[3] - t[3]),
            t[5],
        )
    )

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
    use_estimate_defense=False,
    estimate_scale=1.0,
    use_enemy_radar=False,
    radar_angle_threshold=0.1,
    use_comets_v2=False,      # NEW: enable more selective comet logic v2
    comet_evac_remaining=8,   # NEW: evacuate comets only near expiration
    # DELETED: max_comet_ships / max_comet_distance / min_comet_remaining
    #          are now handled inside get_best_comet_target_v2
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        comet_ids = get_comet_ids(obs)
        evacuated_sources = set()

        # NEW: v2 evacuates owned comets only when they are close to expiration
        if use_comets_v2:
            for comet in my_planets:
                if comet[0] not in comet_ids:
                    continue

                remaining = get_comet_remaining_steps(obs, comet[0])

                if remaining > comet_evac_remaining:
                    continue

                destination = get_nearest_owned_non_comet(
                    source=comet,
                    my_planets=my_planets,
                    comet_ids=comet_ids
                )

                if destination is None:
                    continue

                ships_to_send = comet[5]

                if ships_to_send <= 0:
                    continue

                angle = get_angle(comet, destination)
                moves.append([comet[0], angle, ships_to_send])
                evacuated_sources.add(comet[0])

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            if mine[0] in evacuated_sources:
                continue

            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            if use_enemy_radar:
                available_targets = filter_targets_by_enemy_radar(
                    obs=obs,
                    targets=available_targets,
                    angle_threshold=radar_angle_threshold
                )

                if not available_targets:
                    continue

            # NEW: v2 prioritizes normal targets first
            # DELETED: v1 directly preferred comet targets when available
            if use_comets_v2:
                normal_targets = [
                    t for t in available_targets
                    if t[0] not in comet_ids
                ]

                if normal_targets:
                    nearest = get_nearest_target(mine, normal_targets)
                else:
                    # NEW: comets are used only as fallback targets
                    nearest = get_best_comet_target_v2(
                        mine=mine,
                        available_targets=available_targets,
                        obs=obs,
                        comet_ids=comet_ids,
                    )

                    if nearest is None:
                        continue
            else:
                nearest = get_nearest_target(mine, available_targets)

            ships_needed = nearest[5] + 1

            if nearest[1] not in (-1, player):
                ships_needed += enemy_margin

                if use_estimate_defense:
                    estimated_defense = estimate_target_defense(
                        source=mine,
                        target=nearest,
                        ships_to_send=ships_needed
                    )

                    scaled_estimate = math.ceil(
                        estimated_defense * estimate_scale
                    )

                    ships_needed = max(
                        ships_needed,
                        scaled_estimate + 1
                    )

            if mine[5] >= ships_needed:
                angle = get_angle(mine, nearest)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(nearest[0])

        return moves

    return agent

comet_v2_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
    estimate_scale=0.8,
    use_enemy_radar=True,
    radar_angle_threshold=0.15,
    use_comets_v2=True,
    comet_evac_remaining=8,
)

comet_v2_agent = make_avoid_sun_agent(
    base_agent=comet_v2_core,
    buffer=0.5,
)

comet_v2_agent.__name__ = "early50_angle01_safe5_est08_radar015_cometV2_sun05"

rows = evaluate_against_baseline(
    variant=comet_v2_agent,
    base=base_agent,
    seeds=range(1),
    variant_label=comet_v2_agent.__name__,
    extra_info={
        "logic": "avoid_sun + enemy_safety + estimate + radar + comet_v2",
        "buffer": 0.5,
        "enemy_margin": 5,
        "estimate_scale": 0.8,
        "radar_angle_threshold": 0.15,
        "comet_evac_remaining": 8,
    }
)

comet_v2_df = pd.DataFrame(rows)
display(comet_v2_df)

base_results_2p, base_ts_2p = evaluate_agents(
    agents=[base_agent, "random"],
    my_agent=base_agent,
    seeds=range(1)
)

comet_results_2p, comet_ts_2p = evaluate_agents(
    agents=[comet_v2_agent, "random"],
    my_agent=comet_v2_agent,
    seeds=range(1)
)

df_2p = summarize_results(base_results_2p)
df_2p = summarize_results(comet_results_2p)

base_results_4p, base_ts_4p = evaluate_agents(
    agents=[base_agent, "random", "random", "random"],
    my_agent=base_agent,
    seeds=range(1)
)

comet_results_4p, comet_ts_4p = evaluate_agents(
    agents=[comet_v2_agent, "random", "random", "random"],
    my_agent=comet_v2_agent,
    seeds=range(1)
)

df_4p = summarize_results(base_results_4p)
df_4p = summarize_results(comet_results_4p)

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
    use_estimate_defense=False,
    estimate_scale=1.0,
    use_enemy_radar=False,
    radar_angle_threshold=0.15,
    radar_start_step=0,  # NEW: step from which enemy radar becomes active
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            # NEW: enable radar only after a certain step
            # This keeps early expansion fast, then improves decision quality later
            radar_enabled = (
                use_enemy_radar
                and step >= radar_start_step
            )

            if radar_enabled:
                available_targets = filter_targets_by_enemy_radar(
                    obs=obs,
                    targets=available_targets,
                    angle_threshold=radar_angle_threshold
                )

                if not available_targets:
                    continue

            nearest = get_nearest_target(mine, available_targets)

            ships_needed = nearest[5] + 1

            if nearest[1] not in (-1, player):
                ships_needed += enemy_margin

                if use_estimate_defense:
                    estimated_defense = estimate_target_defense(
                        source=mine,
                        target=nearest,
                        ships_to_send=ships_needed
                    )

                    scaled_estimate = math.ceil(
                        estimated_defense * estimate_scale
                    )

                    ships_needed = max(
                        ships_needed,
                        scaled_estimate + 1
                    )

            if mine[5] >= ships_needed:
                angle = get_angle(mine, nearest)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(nearest[0])

        return moves

    return agent

radar_start_steps = [0, 25, 50, 75, 100]
results_rows = []

for start_step in tqdm(radar_start_steps, desc="Phase Radar Ablation"):
    phase_core = make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False,
        enemy_margin=5,
        use_estimate_defense=True,
        estimate_scale=0.8,
        use_enemy_radar=True,
        radar_angle_threshold=0.15,
        radar_start_step=start_step,
    )

    phase_agent = make_avoid_sun_agent(
        base_agent=phase_core,
        buffer=0.5,
    )

    phase_agent.__name__ = f"early50_angle01_safe5_est08_radar015_start{start_step}_sun05"

    rows = evaluate_against_baseline(
        variant=phase_agent,
        base=base_agent,
        seeds=range(1),
        variant_label=phase_agent.__name__,
        extra_info={
            "logic": "phase_radar",
            "buffer": 0.5,
            "enemy_margin": 5,
            "estimate_scale": 0.8,
            "radar_angle_threshold": 0.15,
            "radar_start_step": start_step,
        }
    )

    results_rows.extend(rows)

phase_radar_df = pd.DataFrame(results_rows)
display(phase_radar_df)

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
    use_estimate_defense=False,
    estimate_scale=1.0,
    use_enemy_radar=False,
    radar_angle_threshold=0.15,
    radar_start_step=0,
    wait_margin=0,  # NEW: minimum ships to keep after sending
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            radar_enabled = (
                use_enemy_radar
                and step >= radar_start_step
            )

            if radar_enabled:
                available_targets = filter_targets_by_enemy_radar(
                    obs=obs,
                    targets=available_targets,
                    angle_threshold=radar_angle_threshold
                )

                if not available_targets:
                    continue

            nearest = get_nearest_target(mine, available_targets)

            ships_needed = nearest[5] + 1

            if nearest[1] not in (-1, player):
                ships_needed += enemy_margin

                if use_estimate_defense:
                    estimated_defense = estimate_target_defense(
                        source=mine,
                        target=nearest,
                        ships_to_send=ships_needed
                    )

                    scaled_estimate = math.ceil(
                        estimated_defense * estimate_scale
                    )

                    ships_needed = max(
                        ships_needed,
                        scaled_estimate + 1
                    )

            # NEW: wait logic
            # Skip the attack if it would leave too few ships on the source planet.
            if wait_margin > 0:
                if ships_needed > mine[5] - wait_margin:
                    continue

            if mine[5] >= ships_needed:
                angle = get_angle(mine, nearest)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(nearest[0])

        return moves

    return agent

wait_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
    estimate_scale=0.8,
    use_enemy_radar=True,
    radar_angle_threshold=0.15,
    radar_start_step=0,
    wait_margin=3,
)

wait_agent = make_avoid_sun_agent(
    base_agent=wait_core,
    buffer=0.5,
)

print(base_agent.__name__ )

wait_margins = [0, 1, 2, 3, 5]
results_rows = []

for margin in tqdm(wait_margins, desc="Wait Margin Ablation"):
    wait_core = make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False,
        enemy_margin=5,
        use_estimate_defense=True,
        estimate_scale=0.8,
        use_enemy_radar=True,
        radar_angle_threshold=0.15,
        radar_start_step=0,
        wait_margin=margin,
    )

    wait_agent = make_avoid_sun_agent(
        base_agent=wait_core,
        buffer=0.5,
    )

    wait_agent.__name__ = f"early50_angle01_safe5_est08_radar015_wait{margin}_sun05"

    rows = evaluate_against_baseline(
        variant=wait_agent,
        base=base_agent,
        seeds=range(1),
        variant_label=wait_agent.__name__,
        extra_info={
            "logic": "wait",
            "wait_margin": margin,
            "enemy_margin": 5,
            "estimate_scale": 0.8,
            "radar_angle_threshold": 0.15,
        }
    )

    results_rows.extend(rows)

wait_df = pd.DataFrame(results_rows)
display(wait_df)

def get_best_value_target(mine, targets, distance_eps=1e-6):
    def score(t):
        distance = math.hypot(mine[2] - t[2], mine[3] - t[3])
        return t[6] / (distance + distance_eps)

    return max(targets, key=score)

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
    use_estimate_defense=False,
    estimate_scale=1.0,
    use_enemy_radar=False,
    radar_angle_threshold=0.15,
    radar_start_step=0,
    wait_margin=0,
    use_best_target=False,  # NEW: enable value-based target selection
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            radar_enabled = (
                use_enemy_radar
                and step >= radar_start_step
            )

            if radar_enabled:
                available_targets = filter_targets_by_enemy_radar(
                    obs=obs,
                    targets=available_targets,
                    angle_threshold=radar_angle_threshold
                )

                if not available_targets:
                    continue

            # NEW: switch target selection strategy
            # nearest → value/distance-based
            if use_best_target:
                target = get_best_value_target(mine, available_targets)
            else:
                target = get_nearest_target(mine, available_targets)

            ships_needed = target[5] + 1

            if target[1] not in (-1, player):
                ships_needed += enemy_margin

                if use_estimate_defense:
                    estimated_defense = estimate_target_defense(
                        source=mine,
                        target=target,
                        ships_to_send=ships_needed
                    )

                    scaled_estimate = math.ceil(
                        estimated_defense * estimate_scale
                    )

                    ships_needed = max(
                        ships_needed,
                        scaled_estimate + 1
                    )

            if wait_margin > 0:
                if ships_needed > mine[5] - wait_margin:
                    continue

            if mine[5] >= ships_needed:
                angle = get_angle(mine, target)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(target[0])

        return moves

    return agent

print(base_agent.__name__ )

best_target_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
    estimate_scale=0.8,
    use_enemy_radar=True,
    radar_angle_threshold=0.15,
    radar_start_step=0,
    wait_margin=0,
    use_best_target=True,
)

best_target_agent = make_avoid_sun_agent(
    base_agent=best_target_core,
    buffer=0.5,
)

best_target_agent.__name__ = "early50_angle01_safe5_est08_radar015_bestTarget_sun05"

rows = evaluate_against_baseline(
    variant=best_target_agent,
    base=base_agent,
    seeds=range(1),
    variant_label=best_target_agent.__name__,
    extra_info={
        "logic": "best_target",
        "enemy_margin": 5,
        "estimate_scale": 0.8,
        "radar_angle_threshold": 0.15,
        "target_score": "production / distance",
    }
)

best_target_df = pd.DataFrame(rows)
display(best_target_df)

def get_best_value_target(mine, targets, score_type="prod_dist", eps=1e-6):
    def score(t):
        dist = math.hypot(mine[2] - t[2], mine[3] - t[3])
        ships = t[5]
        prod = t[6]

        if score_type == "prod_dist":
            return prod / (dist + eps)

        if score_type == "prod_ship_dist":
            return prod / ((ships + 1) * (dist + eps))

        if score_type == "prod_over_ships":
            return prod / (ships + 1)

        if score_type == "nearest":
            return -dist

        raise ValueError(f"Unknown score_type: {score_type}")

    return max(targets, key=score)

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
    use_estimate_defense=False,
    estimate_scale=1.0,
    use_enemy_radar=False,
    radar_angle_threshold=0.15,
    radar_start_step=0,
    wait_margin=0,
    use_best_target=False,
    target_score_type="prod_dist",  # NEW: choose scoring function type
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            radar_enabled = (
                use_enemy_radar
                and step >= radar_start_step
            )

            if radar_enabled:
                available_targets = filter_targets_by_enemy_radar(
                    obs=obs,
                    targets=available_targets,
                    angle_threshold=radar_angle_threshold
                )

                if not available_targets:
                    continue

            # NEW: flexible target selection using multiple scoring functions
            if use_best_target:
                target = get_best_value_target(
                    mine=mine,
                    targets=available_targets,
                    score_type=target_score_type
                )
            else:
                target = get_nearest_target(mine, available_targets)

            ships_needed = target[5] + 1

            if target[1] not in (-1, player):
                ships_needed += enemy_margin

                if use_estimate_defense:
                    estimated_defense = estimate_target_defense(
                        source=mine,
                        target=target,
                        ships_to_send=ships_needed
                    )

                    scaled_estimate = math.ceil(
                        estimated_defense * estimate_scale
                    )

                    ships_needed = max(
                        ships_needed,
                        scaled_estimate + 1
                    )

            if wait_margin > 0:
                if ships_needed > mine[5] - wait_margin:
                    continue

            if mine[5] >= ships_needed:
                angle = get_angle(mine, target)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(target[0])

        return moves

    return agent

score_types = [
    "prod_dist",
    "prod_ship_dist",
    "prod_over_ships",
    "nearest",
]

results_rows = []

for score_type in tqdm(score_types, desc="Target Score Ablation"):
    core = make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False,
        enemy_margin=5,
        use_estimate_defense=True,
        estimate_scale=0.8,
        use_enemy_radar=True,
        radar_angle_threshold=0.15,
        radar_start_step=0,
        wait_margin=0,
        use_best_target=True,
        target_score_type=score_type,
    )

    agent = make_avoid_sun_agent(
        base_agent=core,
        buffer=0.5,
    )

    agent.__name__ = f"early50_safe5_est08_radar015_{score_type}_sun05"

    rows = evaluate_against_baseline(
        variant=agent,
        base=base_agent,
        seeds=range(1),
        variant_label=agent.__name__,
        extra_info={
            "logic": "target_score_ablation",
            "enemy_margin": 5,
            "estimate_scale": 0.8,
            "radar_angle_threshold": 0.15,
            "target_score": score_type,
        }
    )

    results_rows.extend(rows)

target_score_df = pd.DataFrame(results_rows)
display(target_score_df)

print(base_agent.__name__ )

def make_ablation_agent(
    early_off=False,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=0,
    use_estimate_defense=False,
    estimate_scale=1.0,
    use_enemy_radar=False,
    radar_angle_threshold=0.15,
    radar_start_step=0,
    wait_margin=0,
    use_best_target=False,
    target_score_type="prod_dist",
    target_phase_step=0,  # NEW: step from which value-based target selection becomes active
):
    def agent(obs):
        moves = []

        step = obs["step"]
        player = obs["player"]

        my_planets, targets = split_planets(obs)

        if not my_planets or not targets:
            return moves

        if early_off and step < early_off_until:
            reserved_targets = set()
        else:
            reserved_targets = get_reserved_targets(
                obs,
                angle_threshold=angle_threshold,
                use_capture_filter=use_capture_filter
            )

        for mine in my_planets:
            available_targets = [
                t for t in targets if t[0] not in reserved_targets
            ]

            if not available_targets:
                continue

            radar_enabled = (
                use_enemy_radar
                and step >= radar_start_step
            )

            if radar_enabled:
                available_targets = filter_targets_by_enemy_radar(
                    obs=obs,
                    targets=available_targets,
                    angle_threshold=radar_angle_threshold
                )

                if not available_targets:
                    continue

            # NEW: phase-based target selection
            # Early phase uses nearest target for fast expansion.
            # After target_phase_step, use value-based target selection.
            if use_best_target and step >= target_phase_step:
                target = get_best_value_target(
                    mine=mine,
                    targets=available_targets,
                    score_type=target_score_type
                )
            else:
                target = get_nearest_target(mine, available_targets)

            ships_needed = target[5] + 1

            if target[1] not in (-1, player):
                ships_needed += enemy_margin

                if use_estimate_defense:
                    estimated_defense = estimate_target_defense(
                        source=mine,
                        target=target,
                        ships_to_send=ships_needed
                    )

                    scaled_estimate = math.ceil(
                        estimated_defense * estimate_scale
                    )

                    ships_needed = max(
                        ships_needed,
                        scaled_estimate + 1
                    )

            if wait_margin > 0:
                if ships_needed > mine[5] - wait_margin:
                    continue

            if mine[5] >= ships_needed:
                angle = get_angle(mine, target)
                moves.append([mine[0], angle, ships_needed])
                reserved_targets.add(target[0])

        return moves

    return agent

target_phase_steps = [0, 25, 50, 75, 100]
results_rows = []

for phase_step in tqdm(target_phase_steps, desc="Target Phase Ablation"):
    core = make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False,
        enemy_margin=5,
        use_estimate_defense=True,
        estimate_scale=0.8,
        use_enemy_radar=True,
        radar_angle_threshold=0.15,
        radar_start_step=0,
        wait_margin=0,
        use_best_target=True,
        target_score_type="prod_dist",
        target_phase_step=phase_step,
    )

    agent = make_avoid_sun_agent(
        base_agent=core,
        buffer=0.5,
    )

    agent.__name__ = f"early50_safe5_est08_radar015_prodDist_phase{phase_step}_sun05"

    rows = evaluate_against_baseline(
        variant=agent,
        base=base_agent,
        seeds=range(1),
        variant_label=agent.__name__,
        extra_info={
            "logic": "target_phase_ablation",
            "target_score": "prod_dist",
            "target_phase_step": phase_step,
            "enemy_margin": 5,
            "estimate_scale": 0.8,
            "radar_angle_threshold": 0.15,
            "buffer": 0.5,
        }
    )

    results_rows.extend(rows)

target_phase_df = pd.DataFrame(results_rows)
display(target_phase_df)

base_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
    estimate_scale=0.8,
    use_enemy_radar=True,
    radar_angle_threshold=0.15,
    radar_start_step=0,
    wait_margin=0,
    use_best_target=True,
    target_score_type="prod_dist",
    target_phase_step=0,
)

prod_dist_0_agent = make_avoid_sun_agent(
    base_agent=base_core,
    buffer=0.5,
)


prod_dist_0_agent.__name__ = "early50_safe5_est08_radar015_prodDist_phase0_sun05"


variant_core = make_ablation_agent(
    early_off=True,
    early_off_until=50,
    angle_threshold=0.1,
    use_capture_filter=False,
    enemy_margin=5,
    use_estimate_defense=True,
    estimate_scale=0.8,
    use_enemy_radar=True,
    radar_angle_threshold=0.15,
    radar_start_step=0,
    wait_margin=0,
    use_best_target=True,
    target_score_type="prod_dist",
    target_phase_step=25,
)

prod_dist_25_agent = make_avoid_sun_agent(
    base_agent=variant_core,
    buffer=0.5,
)

prod_dist_25_agent.__name__ = "early50_safe5_est08_radar015_prodDist_phase25_sun05"

base = prod_dist_0_agent
variant = prod_dist_25_agent

base_results_2p, base_ts_2p = evaluate_agents(
    agents=[base, "random"],
    my_agent=base,
    seeds=range(1)
)

variant_results_2p, variant_ts_2p = evaluate_agents(
    agents=[variant, "random"],
    my_agent=variant,
    seeds=range(1)
)

df_2p = summarize_results(base_results_2p)
df_2p = summarize_results(variant_results_2p)

base_results_4p, base_ts_4p = evaluate_agents(
    agents=[base, "random", "random", "random"],
    my_agent=base,
    seeds=range(1)
)

variant_results_4p, variant_ts_4p = evaluate_agents(
    agents=[variant, "random", "random", "random"],
    my_agent=variant,
    seeds=range(1)
)

df_4p = summarize_results(base_results_4p)
df_4p = summarize_results(variant_results_4p)

rows = evaluate_against_baseline(
    variant=variant,
    base=base,
    seeds=range(1),
    variant_label=variant.__name__,
)

df = pd.DataFrame(rows)
display(df)

base_agent = base
base_agent.__name__ = "early50_safe5_est08_radar015_prodDist_phase0_sun05"

estimate_scales = [0.6, 0.7, 0.8, 0.9, 1.0]
results_rows = []

for scale in tqdm(estimate_scales, desc="Revisiting Estimate Scale"):
    core = make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False,
        enemy_margin=5,
        use_estimate_defense=True,
        estimate_scale=scale,
        use_enemy_radar=True,
        radar_angle_threshold=0.15,
        radar_start_step=0,
        wait_margin=0,
        use_best_target=True,
        target_score_type="prod_dist",
        target_phase_step=0,
    )

    agent = make_avoid_sun_agent(
        base_agent=core,
        buffer=0.5,
    )

    agent.__name__ = f"early50_safe5_est{scale}_radar015_prodDist_sun05"

    rows = evaluate_against_baseline(
        variant=agent,
        base=base_agent,
        seeds=range(1),
        variant_label=agent.__name__,
        extra_info={
            "logic": "revisit_estimate_scale",
            "estimate_scale": scale,
            "radar_angle_threshold": 0.15,
            "target_score": "prod_dist",
            "buffer": 0.5,
        }
    )

    results_rows.extend(rows)

df = pd.DataFrame(results_rows)
display(df)

radar_thresholds = [0.10, 0.12, 0.15, 0.18, 0.20]
results_rows = []

for th in tqdm(radar_thresholds, desc="Revisiting Radar Threshold"):
    core = make_ablation_agent(
        early_off=True,
        early_off_until=50,
        angle_threshold=0.1,
        use_capture_filter=False,
        enemy_margin=5,
        use_estimate_defense=True,
        estimate_scale=0.8,
        use_enemy_radar=True,
        radar_angle_threshold=th,
        radar_start_step=0,
        wait_margin=0,
        use_best_target=True,
        target_score_type="prod_dist",
        target_phase_step=0,
    )

    agent = make_avoid_sun_agent(
        base_agent=core,
        buffer=0.5,
    )

    agent.__name__ = f"early50_safe5_est08_radar{th}_prodDist_sun05"

    rows = evaluate_against_baseline(
        variant=agent,
        base=base_agent,
        seeds=range(1),
        variant_label=agent.__name__,
        extra_info={
            "logic": "revisit_radar_threshold",
            "estimate_scale": 0.8,
            "radar_angle_threshold": th,
            "target_score": "prod_dist",
            "buffer": 0.5,
        }
    )

    results_rows.extend(rows)

df = pd.DataFrame(results_rows)
display(df)


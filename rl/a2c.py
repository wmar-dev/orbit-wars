"""
T008: A2C (Advantage Actor-Critic) training for Orbit Wars.

Same architecture as PPO (rl/ppo.py) but replaces the clipped PPO loss with a
plain policy gradient loss. No importance sampling, no clipping.
Used as an ablation to quantify the contribution of PPO's clipping.

Usage:
    uv run python rl/a2c.py --episodes 1000 --opponent random
    uv run python rl/a2c.py --episodes 5000 --opponent agent_v38.py --resume
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.distributions import Categorical

sys.path.insert(0, str(Path(__file__).parent.parent))
from rl.env import OrbitWarsEnv
from rl.obs import MAX_PLANETS, OBS_SIZE
from rl.ppo import PolicyNet, RolloutBuffer, get_opponent, _latest_checkpoint

# ---------------------------------------------------------------------------
# A2C-specific hyperparameters (shared with PPO where same)
# ---------------------------------------------------------------------------
HIDDEN   = 256
GAMMA    = 0.99
LAM      = 0.95
ENT_COEF = 0.01
VF_COEF  = 0.5
LR       = 3e-4
MAX_GRAD = 0.5
ROLLOUT_STEPS   = 512
CHECKPOINT_EVERY = 200


def train(args):
    device = torch.device(args.device)
    ckpt_dir = Path(args.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "a2c_train.csv"

    net = PolicyNet().to(device)
    optimizer = optim.Adam(net.parameters(), lr=LR)

    start_episode = 0

    if args.resume:
        latest = _latest_checkpoint(ckpt_dir, "a2c")
        if latest:
            ckpt = torch.load(latest, map_location=device, weights_only=False)
            net.load_state_dict(ckpt["policy_state_dict"])
            start_episode = ckpt.get("episode", 0)
            print(f"Resumed from {latest} (episode {start_episode})")

    csv_exists = log_path.exists()
    csv_file = open(log_path, "a", newline="")
    writer = csv.writer(csv_file)
    if not csv_exists:
        writer.writerow(["episode", "ep_reward", "ep_steps", "elapsed_s", "opponent"])

    buf = RolloutBuffer(ROLLOUT_STEPS, OBS_SIZE)
    episode = start_episode
    opponent = get_opponent(episode, args.opponent, ckpt_dir)
    env = OrbitWarsEnv(opponent=opponent, seed=args.seed)
    obs, _ = env.reset()
    ep_reward = 0.0
    ep_steps  = 0
    ep_start  = time.time()

    print(f"Starting A2C training: {args.episodes} episodes, device={args.device}")

    while episode < start_episode + args.episodes:
        net.eval()
        buf.reset()
        for _ in range(ROLLOUT_STEPS):
            obs_t  = torch.FloatTensor(obs).unsqueeze(0).to(device)
            mask_t = torch.FloatTensor(obs[267:319]).unsqueeze(0).to(device)
            with torch.no_grad():
                action, log_prob, _, value = net.get_action_and_value(obs_t, mask_t)
            action_np = action.cpu().numpy()[0]
            next_obs, reward, done, _, _ = env.step(action_np)
            buf.add(obs, action_np, log_prob.item(), reward, float(done), value.item())
            ep_reward += reward
            ep_steps  += 1
            obs = next_obs
            if done:
                elapsed = time.time() - ep_start
                writer.writerow([episode, f"{ep_reward:.4f}", ep_steps,
                                  f"{elapsed:.1f}", opponent])
                csv_file.flush()
                if episode % 50 == 0:
                    print(f"ep={episode:5d} reward={ep_reward:+.3f} "
                          f"steps={ep_steps} t={elapsed:.1f}s opp={opponent[:20]}")
                episode += 1
                ep_reward = 0.0
                ep_steps  = 0
                ep_start  = time.time()
                if episode % CHECKPOINT_EVERY == 0:
                    ckpt_path = ckpt_dir / f"a2c_ep{episode:05d}.pt"
                    torch.save({
                        "policy_state_dict": net.state_dict(),
                        "episode": episode,
                        "score_vs_v38": None,
                        "algorithm": "a2c",
                    }, ckpt_path)
                    all_ckpts = sorted(ckpt_dir.glob("a2c_ep*.pt"),
                                       key=lambda p: int(p.stem.split("ep")[1]))
                    for old in all_ckpts[:-5]:
                        old.unlink(missing_ok=True)
                    print(f"  Checkpoint saved: {ckpt_path}")
                new_opp = get_opponent(episode, args.opponent, ckpt_dir)
                if new_opp != opponent:
                    opponent = new_opp
                    env.close()
                    env = OrbitWarsEnv(opponent=opponent)
                    print(f"  Opponent updated: {opponent[:30]}")
                obs, _ = env.reset()
                if episode >= start_episode + args.episodes:
                    break

        if episode >= start_episode + args.episodes:
            break

        # A2C update (plain policy gradient — no clipping)
        net.train()
        with torch.no_grad():
            obs_t  = torch.FloatTensor(obs).unsqueeze(0).to(device)
            mask_t = torch.FloatTensor(obs[267:319]).unsqueeze(0).to(device)
            _, _, _, last_val = net.get_action_and_value(obs_t, mask_t)
        advantages, returns = buf.compute_gae(last_val.item(), gamma=GAMMA, lam=LAM)

        obs_b  = torch.FloatTensor(buf.obs[:buf.ptr]).to(device)
        act_b  = torch.LongTensor(buf.actions[:buf.ptr]).to(device)
        adv_b  = torch.FloatTensor(advantages).to(device)
        ret_b  = torch.FloatTensor(returns).to(device)
        mask_b = obs_b[:, 267:319]

        adv_b = (adv_b - adv_b.mean()) / (adv_b.std() + 1e-8)

        _, log_probs, entropy, values = net.get_action_and_value(obs_b, mask_b, action=act_b)

        pg_loss  = -(log_probs * adv_b).mean()
        vf_loss  = (values - ret_b).pow(2).mean()
        ent_loss = -entropy.mean()
        loss = pg_loss + VF_COEF * vf_loss + ENT_COEF * ent_loss

        optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(net.parameters(), MAX_GRAD)
        optimizer.step()

    final_path = ckpt_dir / f"a2c_ep{episode:05d}.pt"
    torch.save({
        "policy_state_dict": net.state_dict(),
        "episode": episode,
        "score_vs_v38": None,
        "algorithm": "a2c",
    }, final_path)
    best_path = ckpt_dir / "a2c_best.pt"
    if not best_path.exists():
        import shutil
        shutil.copy(final_path, best_path)
    print(f"Training complete. Final checkpoint: {final_path}")
    csv_file.close()
    env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes",       type=int, default=1000)
    parser.add_argument("--opponent",       type=str, default="random")
    parser.add_argument("--checkpoint-dir", type=str, default="rl/checkpoints")
    parser.add_argument("--device",         type=str, default="cpu")
    parser.add_argument("--seed",           type=int, default=0)
    parser.add_argument("--resume",         action="store_true")
    args = parser.parse_args()
    train(args)

"""
T007: CleanRL-style PPO training for Orbit Wars.

Usage:
    uv run python rl/ppo.py --episodes 1000 --opponent random
    uv run python rl/ppo.py --episodes 5000 --opponent agent_v38.py --resume

Architecture:
    Shared MLP backbone (2 × 256 ReLU) → actor heads (src, tgt, frac) + value head
    Action masking: -1e9 added to invalid source/target logits before softmax
    GAE: gamma=0.99, lambda=0.95
    PPO clip: epsilon=0.2
"""

import argparse
import csv
import math
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

# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------
HIDDEN     = 256
GAMMA      = 0.99
LAM        = 0.95
CLIP_EPS   = 0.2
ENT_COEF   = 0.01
VF_COEF    = 0.5
LR         = 3e-4
BATCH_SIZE = 64
EPOCHS     = 4
MAX_GRAD   = 0.5
ROLLOUT_STEPS = 512   # steps to collect before each PPO update

CHECKPOINT_EVERY = 200  # episodes
OPPONENT_SCHEDULE = [
    (0,   "random"),
    (200, None),    # filled in at runtime with agent_v38 path
    (500, "self"),  # mixed self-play
]


# ---------------------------------------------------------------------------
# Policy Network
# ---------------------------------------------------------------------------
class PolicyNet(nn.Module):
    def __init__(self, obs_size=OBS_SIZE, hidden=HIDDEN):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(obs_size, hidden), nn.ReLU(),
            nn.Linear(hidden, hidden),   nn.ReLU(),
        )
        self.actor_src  = nn.Linear(hidden, MAX_PLANETS)
        self.actor_tgt  = nn.Linear(hidden, MAX_PLANETS)
        self.actor_frac = nn.Linear(hidden, 5)
        self.critic     = nn.Linear(hidden, 1)

    def forward(self, x, src_mask=None, tgt_mask=None):
        """
        x:        (B, obs_size)
        src_mask: (B, 12) bool — True where source is valid
        tgt_mask: (B, 12) bool — True where target is valid
        Returns: src_logits, tgt_logits, frac_logits, value
        """
        h = self.backbone(x)

        src_logits  = self.actor_src(h)
        tgt_logits  = self.actor_tgt(h)
        frac_logits = self.actor_frac(h)

        if src_mask is not None:
            src_logits = src_logits.masked_fill(~src_mask, -1e9)
        if tgt_mask is not None:
            tgt_logits = tgt_logits.masked_fill(~tgt_mask, -1e9)

        value = self.critic(h).squeeze(-1)
        return src_logits, tgt_logits, frac_logits, value

    def get_action_and_value(self, x, mask, action=None):
        """Sample or evaluate an action.

        mask: (B, 52) float32 obs mask segment
        """
        src_mask = mask[:, :12].bool()
        tgt_mask = mask[:, 12:24].bool()

        # If no valid sources, fall back to allow all (random no-op likely)
        no_src = ~src_mask.any(dim=1, keepdim=True)
        src_mask = src_mask | no_src
        no_tgt = ~tgt_mask.any(dim=1, keepdim=True)
        tgt_mask = tgt_mask | no_tgt

        src_logits, tgt_logits, frac_logits, value = self(x, src_mask, tgt_mask)

        src_dist  = Categorical(logits=src_logits)
        tgt_dist  = Categorical(logits=tgt_logits)
        frac_dist = Categorical(logits=frac_logits)

        if action is None:
            src_a  = src_dist.sample()
            tgt_a  = tgt_dist.sample()
            frac_a = frac_dist.sample()
        else:
            src_a, tgt_a, frac_a = action[:, 0], action[:, 1], action[:, 2]

        log_prob = (src_dist.log_prob(src_a)
                    + tgt_dist.log_prob(tgt_a)
                    + frac_dist.log_prob(frac_a))
        entropy  = (src_dist.entropy()
                    + tgt_dist.entropy()
                    + frac_dist.entropy())

        act = torch.stack([src_a, tgt_a, frac_a], dim=1)
        return act, log_prob, entropy, value


# ---------------------------------------------------------------------------
# Buffer
# ---------------------------------------------------------------------------
class RolloutBuffer:
    def __init__(self, steps, obs_size):
        self.obs      = np.zeros((steps, obs_size), dtype=np.float32)
        self.actions  = np.zeros((steps, 3),        dtype=np.int64)
        self.log_probs= np.zeros(steps,              dtype=np.float32)
        self.rewards  = np.zeros(steps,              dtype=np.float32)
        self.dones    = np.zeros(steps,              dtype=np.float32)
        self.values   = np.zeros(steps,              dtype=np.float32)
        self.ptr = 0

    def add(self, obs, action, log_prob, reward, done, value):
        self.obs[self.ptr]       = obs
        self.actions[self.ptr]   = action
        self.log_probs[self.ptr] = log_prob
        self.rewards[self.ptr]   = reward
        self.dones[self.ptr]     = done
        self.values[self.ptr]    = value
        self.ptr += 1

    def compute_gae(self, last_value, gamma=GAMMA, lam=LAM):
        advantages = np.zeros_like(self.rewards)
        last_gae   = 0.0
        for t in reversed(range(self.ptr)):
            next_val   = last_value if t == self.ptr - 1 else self.values[t + 1]
            next_done  = self.dones[t]
            delta      = self.rewards[t] + gamma * next_val * (1 - next_done) - self.values[t]
            last_gae   = delta + gamma * lam * (1 - next_done) * last_gae
            advantages[t] = last_gae
        returns = advantages + self.values[:self.ptr]
        return advantages[:self.ptr], returns

    def reset(self):
        self.ptr = 0


# ---------------------------------------------------------------------------
# Opponent scheduling
# ---------------------------------------------------------------------------
def get_opponent(episode, strong_opponent, checkpoints_dir):
    """Return the opponent string/path for the given episode."""
    if episode < 200:
        return "random"
    if episode < 500 or strong_opponent is None:
        return strong_opponent or "random"
    # Mixed self-play: 50% latest checkpoint, 50% strong opponent
    import random as _random
    latest = _latest_checkpoint(checkpoints_dir, "ppo")
    if latest and _random.random() < 0.5:
        return str(latest)
    return strong_opponent


def _latest_checkpoint(checkpoints_dir, prefix):
    d = Path(checkpoints_dir)
    cands = sorted(d.glob(f"{prefix}_ep*.pt"), key=lambda p: int(p.stem.split("ep")[1]))
    return cands[-1] if cands else None


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
def train(args):
    device = torch.device(args.device)
    ckpt_dir = Path(args.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "ppo_train.csv"

    net = PolicyNet().to(device)
    optimizer = optim.Adam(net.parameters(), lr=LR)

    start_episode = 0
    best_score = 0.0

    if args.resume:
        latest = _latest_checkpoint(ckpt_dir, "ppo")
        if latest:
            ckpt = torch.load(latest, map_location=device, weights_only=False)
            net.load_state_dict(ckpt["policy_state_dict"])
            start_episode = ckpt.get("episode", 0)
            best_score    = ckpt.get("score_vs_v38", 0.0) or 0.0
            print(f"Resumed from {latest} (episode {start_episode})")

    csv_exists = log_path.exists()
    csv_file = open(log_path, "a", newline="")
    writer = csv.writer(csv_file)
    if not csv_exists:
        writer.writerow(["episode", "ep_reward", "ep_steps", "elapsed_s", "opponent"])

    buf = RolloutBuffer(ROLLOUT_STEPS, OBS_SIZE)
    episode = start_episode
    t0 = time.time()

    # Environment state
    opponent = get_opponent(episode, args.opponent, ckpt_dir)
    env = OrbitWarsEnv(opponent=opponent, seed=args.seed)
    obs, _ = env.reset()
    ep_reward = 0.0
    ep_steps  = 0
    ep_start  = time.time()

    global_step = 0

    print(f"Starting PPO training: {args.episodes} episodes, device={args.device}")

    while episode < start_episode + args.episodes:
        net.eval()
        # Collect rollout
        buf.reset()
        for _ in range(ROLLOUT_STEPS):
            obs_t = torch.FloatTensor(obs).unsqueeze(0).to(device)
            mask_t = torch.FloatTensor(obs[267:319]).unsqueeze(0).to(device)

            with torch.no_grad():
                action, log_prob, _, value = net.get_action_and_value(obs_t, mask_t)

            action_np = action.cpu().numpy()[0]
            next_obs, reward, done, _, _ = env.step(action_np)

            buf.add(obs, action_np, log_prob.item(), reward, float(done), value.item())

            ep_reward += reward
            ep_steps  += 1
            obs = next_obs
            global_step += 1

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

                # Checkpoint
                if episode % CHECKPOINT_EVERY == 0:
                    ckpt_path = ckpt_dir / f"ppo_ep{episode:05d}.pt"
                    torch.save({
                        "policy_state_dict": net.state_dict(),
                        "episode": episode,
                        "score_vs_v38": None,
                        "algorithm": "ppo",
                    }, ckpt_path)
                    # Keep only last 5 + best
                    all_ckpts = sorted(ckpt_dir.glob("ppo_ep*.pt"),
                                       key=lambda p: int(p.stem.split("ep")[1]))
                    for old in all_ckpts[:-5]:
                        old.unlink(missing_ok=True)
                    print(f"  Checkpoint saved: {ckpt_path}")

                # Update opponent
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

        # PPO update
        net.train()
        with torch.no_grad():
            obs_t  = torch.FloatTensor(obs).unsqueeze(0).to(device)
            mask_t = torch.FloatTensor(obs[267:319]).unsqueeze(0).to(device)
            _, _, _, last_val = net.get_action_and_value(obs_t, mask_t)
        advantages, returns = buf.compute_gae(last_val.item())

        obs_b    = torch.FloatTensor(buf.obs[:buf.ptr]).to(device)
        act_b    = torch.LongTensor(buf.actions[:buf.ptr]).to(device)
        logp_b   = torch.FloatTensor(buf.log_probs[:buf.ptr]).to(device)
        adv_b    = torch.FloatTensor(advantages).to(device)
        ret_b    = torch.FloatTensor(returns).to(device)
        mask_b   = obs_b[:, 267:319]

        adv_b = (adv_b - adv_b.mean()) / (adv_b.std() + 1e-8)

        n = obs_b.shape[0]
        for _ in range(EPOCHS):
            idx = torch.randperm(n)
            for start in range(0, n, BATCH_SIZE):
                mb = idx[start:start + BATCH_SIZE]
                _, new_lp, entropy, new_val = net.get_action_and_value(
                    obs_b[mb], mask_b[mb], action=act_b[mb]
                )
                ratio  = (new_lp - logp_b[mb]).exp()
                adv_mb = adv_b[mb]
                pg_loss = -torch.min(
                    ratio * adv_mb,
                    torch.clamp(ratio, 1 - CLIP_EPS, 1 + CLIP_EPS) * adv_mb
                ).mean()
                vf_loss = (new_val - ret_b[mb]).pow(2).mean()
                ent_loss = -entropy.mean()
                loss = pg_loss + VF_COEF * vf_loss + ENT_COEF * ent_loss

                optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(net.parameters(), MAX_GRAD)
                optimizer.step()

    # Final checkpoint
    final_path = ckpt_dir / f"ppo_ep{episode:05d}.pt"
    torch.save({
        "policy_state_dict": net.state_dict(),
        "episode": episode,
        "score_vs_v38": None,
        "algorithm": "ppo",
    }, final_path)
    # Copy as best if no previous best
    best_path = ckpt_dir / "ppo_best.pt"
    if not best_path.exists():
        import shutil
        shutil.copy(final_path, best_path)
    print(f"Training complete. Final checkpoint: {final_path}")
    csv_file.close()
    env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes",       type=int,   default=1000)
    parser.add_argument("--opponent",       type=str,   default="random",
                        help="Path to opponent agent file, or 'random'")
    parser.add_argument("--checkpoint-dir", type=str,   default="rl/checkpoints")
    parser.add_argument("--device",         type=str,   default="cpu")
    parser.add_argument("--seed",           type=int,   default=0)
    parser.add_argument("--resume",         action="store_true")
    args = parser.parse_args()
    train(args)

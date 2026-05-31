"""
T009: DQN with prioritized experience replay for Orbit Wars.

Uses a factored Q-network (independent Q-heads per action dimension) with
action masking, prioritized replay buffer (PER), and a target network.

Usage:
    uv run python rl/dqn.py --episodes 1000 --opponent random
    uv run python rl/dqn.py --episodes 5000 --opponent agent_v38.py --resume
"""

import argparse
import csv
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

sys.path.insert(0, str(Path(__file__).parent.parent))
from rl.env import OrbitWarsEnv
from rl.obs import MAX_PLANETS, OBS_SIZE
from rl.ppo import get_opponent, _latest_checkpoint

# ---------------------------------------------------------------------------
# Hyperparameters
# ---------------------------------------------------------------------------
HIDDEN        = 256
LR            = 1e-4
GAMMA         = 0.99
BUFFER_SIZE   = 10_000
BATCH_SIZE    = 64
TARGET_UPDATE = 200   # steps between target net syncs
EPS_START     = 1.0
EPS_END       = 0.05
EPS_DECAY     = 500   # episodes to decay over
PER_ALPHA     = 0.6
PER_BETA_START= 0.4
PER_BETA_END  = 1.0
MAX_GRAD      = 10.0
CHECKPOINT_EVERY = 200

N_ACTIONS = [MAX_PLANETS, MAX_PLANETS, 5]  # factored heads


# ---------------------------------------------------------------------------
# Q-Network (factored heads)
# ---------------------------------------------------------------------------
class QNet(nn.Module):
    def __init__(self, obs_size=OBS_SIZE, hidden=HIDDEN):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Linear(obs_size, hidden), nn.ReLU(),
            nn.Linear(hidden,   hidden), nn.ReLU(),
        )
        self.q_src  = nn.Linear(hidden, MAX_PLANETS)
        self.q_tgt  = nn.Linear(hidden, MAX_PLANETS)
        self.q_frac = nn.Linear(hidden, 5)

    def forward(self, x, src_mask=None, tgt_mask=None):
        h = self.backbone(x)
        q_src  = self.q_src(h)
        q_tgt  = self.q_tgt(h)
        q_frac = self.q_frac(h)
        if src_mask is not None:
            q_src = q_src.masked_fill(~src_mask, -1e9)
        if tgt_mask is not None:
            q_tgt = q_tgt.masked_fill(~tgt_mask, -1e9)
        return q_src, q_tgt, q_frac

    def select_action(self, x, mask):
        src_mask = mask[:, :12].bool()
        tgt_mask = mask[:, 12:24].bool()
        no_src = ~src_mask.any(dim=1, keepdim=True)
        src_mask = src_mask | no_src
        no_tgt = ~tgt_mask.any(dim=1, keepdim=True)
        tgt_mask = tgt_mask | no_tgt
        q_src, q_tgt, q_frac = self(x, src_mask, tgt_mask)
        return (q_src.argmax(dim=1),
                q_tgt.argmax(dim=1),
                q_frac.argmax(dim=1))


# ---------------------------------------------------------------------------
# Prioritized Replay Buffer
# ---------------------------------------------------------------------------
class PrioritizedReplay:
    def __init__(self, capacity, alpha=PER_ALPHA):
        self.capacity = capacity
        self.alpha    = alpha
        self.buffer   = []
        self.priorities= np.zeros(capacity, dtype=np.float32)
        self.pos      = 0

    def add(self, transition, priority=1.0):
        if len(self.buffer) < self.capacity:
            self.buffer.append(transition)
        else:
            self.buffer[self.pos] = transition
        self.priorities[self.pos] = max(priority, 1e-6) ** self.alpha
        self.pos = (self.pos + 1) % self.capacity

    def sample(self, batch_size, beta=0.4):
        n = len(self.buffer)
        probs = self.priorities[:n]
        probs = probs / probs.sum()
        indices = np.random.choice(n, batch_size, replace=False, p=probs)
        samples = [self.buffer[i] for i in indices]
        weights = (n * probs[indices]) ** (-beta)
        weights = weights / weights.max()
        return samples, indices, weights.astype(np.float32)

    def update_priorities(self, indices, td_errors):
        for i, td in zip(indices, td_errors):
            self.priorities[i] = (abs(td) + 1e-6) ** self.alpha

    def __len__(self):
        return len(self.buffer)


# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------
def train(args):
    device = torch.device(args.device)
    ckpt_dir = Path(args.checkpoint_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "dqn_train.csv"

    net    = QNet().to(device)
    target = QNet().to(device)
    target.load_state_dict(net.state_dict())
    target.eval()
    optimizer = optim.Adam(net.parameters(), lr=LR)

    replay = PrioritizedReplay(BUFFER_SIZE)

    start_episode = 0
    if args.resume:
        latest = _latest_checkpoint(ckpt_dir, "dqn")
        if latest:
            ckpt = torch.load(latest, map_location=device, weights_only=False)
            net.load_state_dict(ckpt["policy_state_dict"])
            target.load_state_dict(ckpt["policy_state_dict"])
            start_episode = ckpt.get("episode", 0)
            print(f"Resumed from {latest} (episode {start_episode})")

    csv_exists = log_path.exists()
    csv_file = open(log_path, "a", newline="")
    writer = csv.writer(csv_file)
    if not csv_exists:
        writer.writerow(["episode", "ep_reward", "ep_steps", "elapsed_s", "opponent", "epsilon"])

    episode    = start_episode
    global_step= 0
    opponent   = get_opponent(episode, args.opponent, ckpt_dir)
    env        = OrbitWarsEnv(opponent=opponent, seed=args.seed)
    obs, _     = env.reset()
    ep_reward  = 0.0
    ep_steps   = 0
    ep_start   = time.time()

    def epsilon(ep):
        t = min(ep / EPS_DECAY, 1.0)
        return EPS_START + t * (EPS_END - EPS_START)

    def beta(ep):
        t = min(ep / args.episodes, 1.0)
        return PER_BETA_START + t * (PER_BETA_END - PER_BETA_START)

    print(f"Starting DQN training: {args.episodes} episodes, device={args.device}")

    while episode < start_episode + args.episodes:
        eps = epsilon(episode - start_episode)

        obs_t  = torch.FloatTensor(obs).unsqueeze(0).to(device)
        mask_t = torch.FloatTensor(obs[267:319]).unsqueeze(0).to(device)

        if random.random() < eps:
            action_np = np.array([
                random.randrange(MAX_PLANETS),
                random.randrange(MAX_PLANETS),
                random.randrange(5),
            ])
        else:
            with torch.no_grad():
                s, t, f = net.select_action(obs_t, mask_t)
            action_np = np.array([s.item(), t.item(), f.item()])

        next_obs, reward, done, _, _ = env.step(action_np)
        replay.add((obs, action_np, reward, next_obs, float(done)))
        ep_reward += reward
        ep_steps  += 1
        obs = next_obs
        global_step += 1

        # Update target net
        if global_step % TARGET_UPDATE == 0:
            target.load_state_dict(net.state_dict())

        # Training step
        if len(replay) >= BATCH_SIZE:
            b = beta(episode - start_episode)
            samples, indices, weights = replay.sample(BATCH_SIZE, beta=b)
            obs_b, act_b, rew_b, nobs_b, done_b = zip(*samples)

            obs_b   = torch.FloatTensor(np.array(obs_b)).to(device)
            act_b   = torch.LongTensor(np.array(act_b)).to(device)
            rew_b   = torch.FloatTensor(np.array(rew_b)).to(device)
            nobs_b  = torch.FloatTensor(np.array(nobs_b)).to(device)
            done_b  = torch.FloatTensor(np.array(done_b)).to(device)
            weights_t = torch.FloatTensor(weights).to(device)

            nmask_b = nobs_b[:, 267:319]
            with torch.no_grad():
                ns, nt, nf    = target.select_action(nobs_b, nmask_b)
                tq_src, tq_tgt, tq_frac = target(nobs_b,
                    nmask_b[:, :12].bool() | ~nmask_b[:, :12].bool(),  # allow all for target
                    nmask_b[:, 12:24].bool() | ~nmask_b[:, 12:24].bool()
                )
                next_q = (
                    tq_src.gather(1, ns.unsqueeze(1)).squeeze()
                    + tq_tgt.gather(1, nt.unsqueeze(1)).squeeze()
                    + tq_frac.gather(1, nf.unsqueeze(1)).squeeze()
                ) / 3.0
                target_q = rew_b + GAMMA * next_q * (1 - done_b)

            mask_b_t = obs_b[:, 267:319]
            src_mask = mask_b_t[:, :12].bool()
            tgt_mask = mask_b_t[:, 12:24].bool()
            no_src = ~src_mask.any(dim=1, keepdim=True)
            src_mask = src_mask | no_src
            no_tgt = ~tgt_mask.any(dim=1, keepdim=True)
            tgt_mask = tgt_mask | no_tgt

            q_src, q_tgt, q_frac = net(obs_b, src_mask, tgt_mask)
            cur_q = (
                q_src.gather(1, act_b[:, 0].unsqueeze(1)).squeeze()
                + q_tgt.gather(1, act_b[:, 1].unsqueeze(1)).squeeze()
                + q_frac.gather(1, act_b[:, 2].unsqueeze(1)).squeeze()
            ) / 3.0

            td_errors = (cur_q - target_q).detach().cpu().numpy()
            replay.update_priorities(indices, td_errors)

            loss = (weights_t * (cur_q - target_q).pow(2)).mean()
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(net.parameters(), MAX_GRAD)
            optimizer.step()

        if done:
            elapsed = time.time() - ep_start
            writer.writerow([episode, f"{ep_reward:.4f}", ep_steps,
                              f"{elapsed:.1f}", opponent, f"{eps:.3f}"])
            csv_file.flush()
            if episode % 50 == 0:
                print(f"ep={episode:5d} reward={ep_reward:+.3f} "
                      f"steps={ep_steps} eps={eps:.3f} opp={opponent[:20]}")
            episode += 1
            ep_reward = 0.0
            ep_steps  = 0
            ep_start  = time.time()

            if episode % CHECKPOINT_EVERY == 0:
                ckpt_path = ckpt_dir / f"dqn_ep{episode:05d}.pt"
                torch.save({
                    "policy_state_dict": net.state_dict(),
                    "episode": episode,
                    "score_vs_v38": None,
                    "algorithm": "dqn",
                }, ckpt_path)
                all_ckpts = sorted(ckpt_dir.glob("dqn_ep*.pt"),
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

    final_path = ckpt_dir / f"dqn_ep{episode:05d}.pt"
    torch.save({
        "policy_state_dict": net.state_dict(),
        "episode": episode,
        "score_vs_v38": None,
        "algorithm": "dqn",
    }, final_path)
    best_path = ckpt_dir / "dqn_best.pt"
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

"""
Behavioral cloning: supervised pretraining of PolicyNet on v38 demonstrations.
"""

import argparse
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np

from rl.obs import OBS_SIZE, NUM_FLEETS_PER_TURN
from rl.ppo import PolicyNet, save_checkpoint, _save_torch_compat

LR = 1e-3
BATCH_SIZE = 512
EPOCHS = 100


def bc_loss_fn(net, obs_b, act_b, mask_b):
    """
    Cross-entropy loss for behavioral cloning.
    NOTE: No action mask applied — let the network learn from raw logits.
    The mask is only used during RL fine-tuning decode_action.
    Without masking, 2.2% of v38 actions that violate garrison floor (comet
    evacuation, etc.) don't produce ~1e9 loss that dominates gradients.
    """
    src_logits_list, tgt_logits_list, frac_logits_list, _ = net(obs_b)

    loss = 0.0
    for i in range(NUM_FLEETS_PER_TURN):
        src_a = act_b[:, i * 3]
        tgt_a = act_b[:, i * 3 + 1]
        frac_a = act_b[:, i * 3 + 2]
        loss += nn.losses.cross_entropy(src_logits_list[i], src_a.astype(mx.int32)).mean()
        loss += nn.losses.cross_entropy(tgt_logits_list[i], tgt_a.astype(mx.int32)).mean()
        loss += nn.losses.cross_entropy(frac_logits_list[i], frac_a.astype(mx.int32)).mean()
    return loss / NUM_FLEETS_PER_TURN, None


def train(args):
    print(f"Loading dataset from {args.data}...")
    data = np.load(args.data)
    obs = data["obs"]
    actions = data["actions"]
    n_samples = len(obs)
    print(f"  {n_samples} samples, obs dim {obs.shape[1]}, action dim {actions.shape[1]}")

    net = PolicyNet()
    mx.eval(net.parameters())
    optimizer = optim.Adam(learning_rate=args.lr)
    loss_and_grad_fn = nn.value_and_grad(net, bc_loss_fn)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    obs_mx = mx.array(obs, dtype=mx.float32)
    act_mx = mx.array(actions, dtype=mx.int32)
    mask_mx = obs_mx[:, 480:560]

    best_loss = float('inf')
    for epoch in range(1, args.epochs + 1):
        idx = np.random.permutation(n_samples)
        total_loss = 0.0
        n_batches = 0
        t0 = time.time()

        for start in range(0, n_samples, args.batch_size):
            mb = idx[start:start + args.batch_size]
            mb_mx = mx.array(mb)
            (loss_val, _), grads = loss_and_grad_fn(
                net, obs_mx[mb_mx], act_mx[mb_mx], mask_mx[mb_mx]
            )
            optimizer.update(net, grads)
            mx.eval(net.parameters(), optimizer.state, loss_val)
            total_loss += float(loss_val)
            n_batches += 1

        avg_loss = total_loss / n_batches
        elapsed = time.time() - t0
        print(f"epoch {epoch:3d}/{args.epochs} loss={avg_loss:.4f} t={elapsed:.1f}s")

        if avg_loss < best_loss:
            best_loss = avg_loss
            save_checkpoint(net, epoch, best_loss, out_dir / "bc_best.npz")
            _save_torch_compat(net, out_dir / "bc_best.pt", epoch)
            print(f"  down new best ({best_loss:.4f})")

    save_checkpoint(net, args.epochs, avg_loss, out_dir / "bc_final.npz")
    _save_torch_compat(net, out_dir / "bc_final.pt", args.epochs)
    print("BC training complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, default="rl/data/demos.npz")
    parser.add_argument("--output-dir", type=str, default="rl/checkpoints")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE)
    parser.add_argument("--lr", type=float, default=LR)
    args = parser.parse_args()
    train(args)

"""训练 / 验证 / 测试的核心循环。"""

import time

import numpy as np
import torch
from tqdm import tqdm

from .metrics import compute_metrics
from .misc import AverageMeter


def train_one_epoch(model, loader, criterion, optimizer, scaler, device, epoch, use_amp=False):
    model.train()
    loss_meter = AverageMeter("loss")
    acc_meter = AverageMeter("acc")
    start = time.time()

    progress = tqdm(loader, desc=f"Epoch {epoch:03d} train", leave=False, dynamic_ncols=True)
    for images, targets in progress:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        batch_size = images.size(0)

        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type=device.type, enabled=use_amp):
            outputs = model(images)
            loss = criterion(outputs, targets)

        if use_amp:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()

        with torch.no_grad():
            preds = outputs.argmax(dim=1)
            correct = (preds == targets).sum().item()

        loss_meter.update(loss.item(), batch_size)
        acc_meter.update(correct / batch_size, batch_size)
        progress.set_postfix(
            loss=f"{loss_meter.avg:.4f}",
            acc=f"{acc_meter.avg * 100:.2f}%",
            lr=f"{optimizer.param_groups[0]['lr']:.2e}",
        )

    return {
        "loss": loss_meter.avg,
        "acc": acc_meter.avg,
        "time": time.time() - start,
        "num_samples": loss_meter.count,
    }


@torch.no_grad()
def evaluate(model, loader, criterion, device, num_classes, desc="val", use_amp=False):
    model.eval()
    loss_meter = AverageMeter("loss")
    all_preds = []
    all_labels = []
    start = time.time()

    progress = tqdm(loader, desc=desc, leave=False, dynamic_ncols=True)
    for images, targets in progress:
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)

        with torch.autocast(device_type=device.type, enabled=use_amp):
            outputs = model(images)
            loss = criterion(outputs, targets)

        loss_meter.update(loss.item(), images.size(0))
        all_preds.append(outputs.argmax(dim=1).cpu().numpy())
        all_labels.append(targets.cpu().numpy())
        progress.set_postfix(loss=f"{loss_meter.avg:.4f}")

    labels = np.concatenate(all_labels) if all_labels else np.array([], dtype=np.int64)
    preds = np.concatenate(all_preds) if all_preds else np.array([], dtype=np.int64)

    metrics = compute_metrics(labels, preds, num_classes)
    metrics.update({"loss": loss_meter.avg, "time": time.time() - start, "num_samples": int(labels.size)})
    return metrics

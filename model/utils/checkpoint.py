"""断点（checkpoint）保存与加载。

每次保存的 state 至少包含：
    epoch / model / optimizer / scheduler / scaler / best_acc / best_epoch /
    classes / model_name / args / history
"""

import os
from pathlib import Path

import torch


def save_checkpoint(path, state: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Windows 下 torch C++ 文件写入不支持含中文等非 ASCII 字符的路径，
    # 统一通过 Python 文件对象读写（torch 官方支持）。
    # 先写临时文件再原子替换，避免中断时损坏已有断点。
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "wb") as f:
        torch.save(state, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return path


def load_checkpoint(path, device="cpu") -> dict:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"checkpoint 不存在: {path}")
    with open(path, "rb") as f:
        return torch.load(f, map_location=device)

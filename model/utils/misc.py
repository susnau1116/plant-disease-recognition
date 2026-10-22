"""通用工具：随机种子、设备、显存/参数统计等。"""

import random
import time

import numpy as np
import torch


def set_seed(seed: int) -> None:
    """固定所有随机源，保证实验可复现。"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if torch.cuda.is_available():
        torch.backends.cudnn.benchmark = True


def get_device(name: str = "auto") -> torch.device:
    if name == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(name)


def count_parameters(model) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def now_str() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def format_duration(seconds: float) -> str:
    """把秒数格式化为易读时长，如 '2 小时 35 分'、'18 分 20 秒'。"""
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours} 小时 {minutes} 分"
    if minutes > 0:
        return f"{minutes} 分 {secs} 秒"
    return f"{secs} 秒"


class AverageMeter:
    """滑动平均统计（loss/acc 等）。"""

    def __init__(self, name: str = ""):
        self.name = name
        self.reset()

    def reset(self) -> None:
        self.val = 0.0
        self.avg = 0.0
        self.sum = 0.0
        self.count = 0

    def update(self, val, n: int = 1) -> None:
        self.val = float(val)
        self.sum += float(val) * n
        self.count += n
        self.avg = self.sum / max(self.count, 1)

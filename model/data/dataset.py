"""PlantVillage 数据集加载、分层划分与 DataLoader 构建。"""

import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import datasets as tv_datasets

from .transforms import build_eval_transform, build_train_transform

SPLIT_DIR = Path(__file__).resolve().parent / "splits"
RATIOS = (0.7, 0.15, 0.15)


class PlantVillageDataset(Dataset):
    """基于 (相对路径, 标签) 列表的叶片图像数据集。"""

    def __init__(self, root, samples, transform=None):
        self.root = Path(root)
        self.samples = [(str(path), int(label)) for path, label in samples]
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        rel_path, label = self.samples[index]
        image = Image.open(self.root / rel_path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, label

    def labels(self):
        return [label for _, label in self.samples]


def scan_dataset(root):
    """扫描数据集目录，返回 [(相对路径, 标签)], 类别列表。"""
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"数据集目录不存在: {root}")
    folder = tv_datasets.ImageFolder(str(root))
    samples = [(str(Path(path).relative_to(root)), target) for path, target in folder.samples]
    return samples, list(folder.classes)


def stratified_split(samples, ratios=RATIOS, seed: int = 42):
    """按类别分层划分数据集，保证每个类别在三个划分中的比例一致。"""
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError(f"划分比例之和必须为 1: {ratios}")

    rng = random.Random(seed)
    by_class = defaultdict(list)
    for rel_path, label in samples:
        by_class[label].append(rel_path)

    splits = [[], [], []]
    for label in sorted(by_class):
        paths = sorted(by_class[label])
        rng.shuffle(paths)
        total = len(paths)
        num_train = min(total, int(round(total * ratios[0])))
        num_val = min(total - num_train, int(round(total * ratios[1])))
        buckets = [
            paths[:num_train],
            paths[num_train:num_train + num_val],
            paths[num_train + num_val:],
        ]
        for bucket, split in zip(buckets, splits):
            split.extend((path, label) for path in bucket)

    for split in splits:
        rng.shuffle(split)
    return [list(split) for split in splits]


def load_or_create_split(root, split_file=None, ratios=RATIOS, seed: int = 42, resplit: bool = False):
    """加载缓存的划分文件；不存在或 --resplit 时重新分层划分并缓存（保证实验可复现）。"""
    root = Path(root).expanduser().resolve()
    if split_file is None:
        ratio_tag = "_".join(str(round(ratio * 100)) for ratio in ratios)
        split_file = SPLIT_DIR / f"plantvillage_r{ratio_tag}_seed{seed}.json"
    split_file = Path(split_file)

    if split_file.exists() and not resplit:
        payload = json.loads(split_file.read_text(encoding="utf-8"))
        classes = payload.get("classes", [])
        if classes and classes == scan_dataset(root)[1]:
            splits = [payload.get(key, []) for key in ("train", "val", "test")]
            return [[list(item) for item in split] for split in splits], classes, split_file

    samples, classes = scan_dataset(root)
    train_samples, val_samples, test_samples = stratified_split(samples, ratios=ratios, seed=seed)

    payload = {
        "root": str(root),
        "ratios": list(ratios),
        "seed": seed,
        "classes": classes,
        "counts": {
            "train": len(train_samples),
            "val": len(val_samples),
            "test": len(test_samples),
        },
        "train": train_samples,
        "val": val_samples,
        "test": test_samples,
    }
    split_file.parent.mkdir(parents=True, exist_ok=True)
    split_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return [train_samples, val_samples, test_samples], classes, split_file


def limit_split(split, limit: int, seed: int = 42):
    """调试用：随机截取不超过 limit 条样本（不写入划分缓存）。"""
    if not limit or limit <= 0 or len(split) <= limit:
        return split
    rng = random.Random(seed)
    return rng.sample(list(split), limit)


def compute_class_weights(samples, num_classes: int):
    """按类别频率计算交叉熵权重（样本越少权重越大），用于缓解类别不平衡。"""
    labels = np.asarray([int(label) for _, label in samples], dtype=np.int64)
    counts = np.bincount(labels, minlength=num_classes).astype(np.float64)
    weights = counts.sum() / (num_classes * np.maximum(counts, 1.0))
    return torch.tensor(weights, dtype=torch.float32), counts


def build_dataloaders(
    train_samples,
    val_samples,
    test_samples,
    root,
    img_size: int = 224,
    batch_size: int = 32,
    num_workers: int = 4,
    weighted_sampler: bool = False,
    num_classes: int = 38,
):
    train_set = PlantVillageDataset(root, train_samples, transform=build_train_transform(img_size))
    val_set = PlantVillageDataset(root, val_samples, transform=build_eval_transform(img_size))
    test_set = PlantVillageDataset(root, test_samples, transform=build_eval_transform(img_size))

    sampler = None
    shuffle = True
    if weighted_sampler:
        labels = np.asarray(train_set.labels(), dtype=np.int64)
        counts = np.bincount(labels, minlength=num_classes)
        class_weights = 1.0 / np.maximum(counts, 1)
        sample_weights = torch.as_tensor(class_weights[labels], dtype=torch.double)
        sampler = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
        shuffle = False

    loader_kwargs = dict(
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
    )
    if num_workers > 0:
        loader_kwargs.update(persistent_workers=True, prefetch_factor=2)

    train_loader = DataLoader(
        train_set,
        shuffle=shuffle,
        sampler=sampler,
        drop_last=len(train_set) >= batch_size,
        **loader_kwargs,
    )
    val_loader = DataLoader(val_set, shuffle=False, **loader_kwargs)
    test_loader = DataLoader(test_set, shuffle=False, **loader_kwargs)
    return train_loader, val_loader, test_loader

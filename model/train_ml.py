"""传统机器学习对比实验：SVM / KNN / 决策树 / 随机森林。

使用预训练 CNN（默认 ResNet18 ImageNet 权重）提取深度特征
（全局平均池化向量，512 维），再分别训练传统分类器，
用测试集与端到端微调的深度网络（train.py）对比。
特征向量会缓存到 features/ 目录，重复运行无需重新提取。

用法：
    python train_ml.py                                  # 全量特征 + 全部分类器
    python train_ml.py --limit 2000                     # 小样本快速验证
    python train_ml.py --classifiers SVM KNN            # 只跑部分分类器
    python train_ml.py --checkpoint checkpoints/resnet18/best.pth   # 用自己训练的模型提特征
"""

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm

from data.dataset import PlantVillageDataset, limit_split, load_or_create_split
from data.transforms import build_eval_transform
from nets.zoo import MODEL_ZOO, build_backbone, build_model
from utils.checkpoint import load_checkpoint
from utils.logger import setup_logger
from utils.metrics import compute_metrics
from utils.misc import get_device, now_str, set_seed
from utils.report import report_test

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "PlantVillage"
CLASSIFIER_NAMES = ["SVM", "SVM-RBF", "KNN", "DecisionTree", "RandomForest"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="传统机器学习对比实验（深度特征 + 经典分类器）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--backbone", default=None, choices=list(MODEL_ZOO), help="特征提取网络，默认 resnet18")
    parser.add_argument("--checkpoint", default=None, help="用训练好的模型（best.pth）提取特征；不指定则用 ImageNet 预训练权重")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="PlantVillage 数据集目录")
    parser.add_argument("--log-dir", default=str(MODEL_DIR / "logs" / "ml"), help="结果保存目录")
    parser.add_argument("--feature-dir", default=str(MODEL_DIR / "features"), help="特征缓存目录")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--limit", type=int, default=0, help="调试用：每个划分最多使用 N 张图片（0 为全部）")
    parser.add_argument("--classifiers", nargs="+", default=CLASSIFIER_NAMES, choices=CLASSIFIER_NAMES, help="要训练的分类器")
    parser.add_argument("--rbf-samples", type=int, default=8000, help="SVM-RBF 训练样本上限（核方法复杂度高，默认分层抽样）")
    parser.add_argument("--no-pretrained", action="store_true", help="不使用 ImageNet 预训练权重（仅在不指定 --checkpoint 时生效）")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resplit", action="store_true", help="忽略缓存，重新划分数据集")
    parser.add_argument("--split-file", default=None, help="数据集划分缓存文件路径")
    parser.add_argument("--device", default="auto", help="auto / cuda / cpu")
    return parser.parse_args()


def build_loaders(train_samples, test_samples, root, img_size, batch_size, num_workers):
    transform = build_eval_transform(img_size)
    train_set = PlantVillageDataset(root, train_samples, transform=transform)
    test_set = PlantVillageDataset(root, test_samples, transform=transform)

    loader_kwargs = dict(
        batch_size=batch_size,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available(),
        shuffle=False,
    )
    if num_workers > 0:
        loader_kwargs.update(persistent_workers=True, prefetch_factor=2)
    return DataLoader(train_set, **loader_kwargs), DataLoader(test_set, **loader_kwargs)


def load_extractor(args, num_classes, device):
    """构建特征提取器（不含分类头），返回 (backbone 名称, 模型)。"""
    if args.checkpoint:
        state = load_checkpoint(args.checkpoint, device)
        ckpt_backbone = state.get("model_name")
        backbone = args.backbone or ckpt_backbone or "resnet18"
        if args.backbone and ckpt_backbone and args.backbone != ckpt_backbone:
            raise ValueError(f"权重由 {ckpt_backbone} 训练，与 --backbone {args.backbone} 不一致")
        model = build_model(backbone, num_classes=num_classes, pretrained=False)
        model.load_state_dict(state["model"])
    else:
        backbone = args.backbone or "resnet18"
        model = build_model(backbone, num_classes=num_classes, pretrained=not args.no_pretrained)
    extractor = nn.Sequential(*list(model.children())[:-1])
    return backbone, extractor.to(device).eval()


@torch.no_grad()
def extract_features(extractor, loader, device, desc):
    features, labels = [], []
    for images, targets in tqdm(loader, desc=desc, leave=False, dynamic_ncols=True):
        output = extractor(images.to(device, non_blocking=True))
        output = F.adaptive_avg_pool2d(output, 1)
        features.append(torch.flatten(output, 1).cpu().numpy())
        labels.append(targets.numpy())
    return np.concatenate(features), np.concatenate(labels)


def load_or_extract_features(args, backbone, extractor, train_loader, test_loader, classes, device, logger):
    feature_dir = Path(args.feature_dir)
    feature_dir.mkdir(parents=True, exist_ok=True)
    source = "finetuned" if args.checkpoint else "imagenet"
    limit_tag = f"_limit{args.limit}" if args.limit > 0 else ""
    cache_path = feature_dir / f"{backbone}_{source}{limit_tag}_img{args.img_size}.npz"

    if cache_path.exists():
        cached = np.load(cache_path, allow_pickle=True)
        if list(cached["classes"]) == list(classes):
            logger.info(f"加载特征缓存: {cache_path}")
            return cached["train_x"], cached["train_y"], cached["test_x"], cached["test_y"]

    logger.info(f"提取特征（{backbone}，{source} 权重），首次运行约 10 分钟...")
    train_x, train_y = extract_features(extractor, train_loader, device, f"{backbone} train")
    test_x, test_y = extract_features(extractor, test_loader, device, f"{backbone} test")
    np.savez(cache_path, train_x=train_x, train_y=train_y, test_x=test_x, test_y=test_y, classes=np.array(classes))
    logger.info(f"特征已缓存: {cache_path} | 训练 {train_x.shape} | 测试 {test_x.shape}")
    return train_x, train_y, test_x, test_y


def build_classifiers(names, seed):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC, LinearSVC
    from sklearn.tree import DecisionTreeClassifier

    classifiers = {}
    for name in names:
        if name == "SVM":
            classifiers[name] = make_pipeline(
                StandardScaler(),
                LinearSVC(C=1.0, max_iter=3000, class_weight="balanced", dual="auto"),
            )
        elif name == "SVM-RBF":
            classifiers[name] = make_pipeline(
                StandardScaler(),
                SVC(C=10.0, kernel="rbf", gamma="scale", class_weight="balanced"),
            )
        elif name == "KNN":
            classifiers[name] = make_pipeline(
                StandardScaler(),
                KNeighborsClassifier(n_neighbors=5, n_jobs=-1),
            )
        elif name == "DecisionTree":
            classifiers[name] = DecisionTreeClassifier(random_state=seed, class_weight="balanced")
        elif name == "RandomForest":
            classifiers[name] = RandomForestClassifier(
                n_estimators=300, n_jobs=-1, random_state=seed, class_weight="balanced"
            )
    return classifiers


def stratified_subsample(features, labels, max_samples, seed):
    """按类别分层抽样，控制 SVM-RBF 的训练规模。"""
    if max_samples <= 0 or len(labels) <= max_samples:
        return features, labels
    rng = np.random.default_rng(seed)
    selected = []
    for label in np.unique(labels):
        indices = np.where(labels == label)[0]
        take = max(1, int(round(len(indices) * max_samples / len(labels))))
        selected.extend(rng.choice(indices, size=min(take, len(indices)), replace=False))
    selected = np.sort(np.array(selected))
    return features[selected], labels[selected]


def write_comparison_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    args = parse_args()
    device = get_device(args.device)
    set_seed(args.seed)

    log_dir = Path(args.log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(log_dir / f"train_ml_{now_str()}.log")

    logger.info("=" * 72)
    logger.info("传统机器学习对比实验（深度特征 + 经典分类器）")
    logger.info(f"设备: {device} | 参数: {json.dumps(vars(args), ensure_ascii=False)}")

    data_dir = Path(args.data_dir).expanduser()
    if not data_dir.is_absolute():
        data_dir = (PROJECT_ROOT / data_dir).resolve()
    (train_samples, val_samples, test_samples), classes, split_file = load_or_create_split(
        data_dir, split_file=args.split_file, ratios=(0.7, 0.15, 0.15), seed=args.seed, resplit=args.resplit
    )
    num_classes = len(classes)
    if args.limit > 0:
        train_samples = limit_split(train_samples, args.limit, args.seed)
        test_samples = limit_split(test_samples, args.limit, args.seed + 1)
    logger.info(f"数据集: {data_dir} | 划分文件: {split_file}")
    logger.info(f"特征提取样本数: 训练 {len(train_samples)} | 测试 {len(test_samples)} | 类别 {num_classes}")

    train_loader, test_loader = build_loaders(
        train_samples, test_samples, data_dir, args.img_size, args.batch_size, args.num_workers
    )
    backbone, extractor = load_extractor(args, num_classes, device)
    logger.info(f"特征提取网络: {backbone}（{'自训练权重 ' + str(args.checkpoint) if args.checkpoint else 'ImageNet 预训练权重'}）")

    train_x, train_y, test_x, test_y = load_or_extract_features(
        args, backbone, extractor, train_loader, test_loader, classes, device, logger
    )
    del extractor
    torch.cuda.empty_cache() if torch.cuda.is_available() else None

    classifiers = build_classifiers(args.classifiers, args.seed)
    rows = []
    for name, classifier in classifiers.items():
        fit_x, fit_y = train_x, train_y
        if name == "SVM-RBF":
            fit_x, fit_y = stratified_subsample(train_x, train_y, args.rbf_samples, args.seed)
        logger.info(f"[{name}] 开始训练（训练样本 {len(fit_y)}）...")
        start = time.time()
        classifier.fit(fit_x, fit_y)
        train_sec = time.time() - start
        start = time.time()
        preds = classifier.predict(test_x)
        predict_sec = time.time() - start

        metrics = compute_metrics(test_y, preds, num_classes)
        metrics["num_samples"] = int(test_y.size)
        logger.info(f"[{name}] 训练 {train_sec:.1f}s | 预测 {predict_sec:.1f}s")
        report_test(logger, metrics, classes, log_dir / name)

        rows.append({
            "classifier": name,
            "accuracy": round(metrics["accuracy"], 6),
            "macro_precision": round(metrics["macro_precision"], 6),
            "macro_recall": round(metrics["macro_recall"], 6),
            "macro_f1": round(metrics["macro_f1"], 6),
            "weighted_f1": round(metrics["weighted_f1"], 6),
            "num_train": len(fit_y),
            "num_test": int(test_y.size),
            "train_sec": round(train_sec, 1),
            "predict_sec": round(predict_sec, 1),
        })

    rows.sort(key=lambda row: row["accuracy"], reverse=True)
    write_comparison_csv(log_dir / "comparison.csv", rows)

    logger.info("=" * 72)
    logger.info("对比结果（按测试集准确率排序）:")
    for row in rows:
        logger.info(
            f"{row['classifier']:<14} acc {row['accuracy'] * 100:.2f}% | "
            f"macro-F1 {row['macro_f1'] * 100:.2f}% | 训练样本 {row['num_train']}"
        )
    logger.info(f"对比表已保存: {log_dir / 'comparison.csv'}")


if __name__ == "__main__":
    main()

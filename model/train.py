"""农作物病害识别模型训练脚本（支持断点续训）。

特性：
- ResNet18 / ResNet34 / ResNet50 ImageNet 迁移学习
- 7:1.5:1.5 分层数据集划分，划分结果缓存，保证多次实验数据一致
- 类别加权损失 / 加权采样，缓解 PlantVillage 类别不平衡
- 数据增强：随机裁剪、翻转、旋转、色彩抖动、高斯噪声、随机擦除
- Adam + CosineAnnealingLR（带 warmup）、标签平滑、混合精度（CUDA）
- 每个 epoch 保存 last.pth / best.pth，--resume 断点续训
- 早停；训练结束后自动用最优权重评估测试集
  （准确率 / 精确率 / 召回率 / F1 / 混淆矩阵）

用法：
    python train.py --model resnet18 --epochs 30 --batch-size 32
    python train.py --model resnet50 --epochs 30 --batch-size 32
    python train.py --resume auto          # 断点续训
    python train.py --resume auto --stop-after 2   # 续训 2 个 epoch（2 个断点）后自动停止
    python train.py --test-only            # 仅加载最优权重评估测试集
"""

import argparse
import json
import math
from pathlib import Path

import torch
import torch.nn as nn

from data.dataset import (
    build_dataloaders,
    compute_class_weights,
    limit_split,
    load_or_create_split,
)
from nets.zoo import MODEL_ZOO, build_model
from utils.checkpoint import load_checkpoint, save_checkpoint
from utils.engine import evaluate, train_one_epoch
from utils.logger import setup_logger, write_history_csv
from utils.misc import count_parameters, format_duration, get_device, now_str, set_seed
from utils.report import report_test

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "PlantVillage"


def parse_args():
    parser = argparse.ArgumentParser(
        description="农作物病害识别深度学习训练（支持断点续训）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--model", default=None, choices=list(MODEL_ZOO), help="网络结构，默认 resnet18；test-only 时可从权重推断")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="PlantVillage 数据集目录")
    parser.add_argument("--save-dir", default=str(MODEL_DIR / "checkpoints"), help="权重保存目录")
    parser.add_argument("--log-dir", default=str(MODEL_DIR / "logs"), help="日志保存目录")
    parser.add_argument("--tag", default=None, help="实验名称（默认与模型同名）")
    parser.add_argument("--epochs", type=int, default=30, help="训练总轮数")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3, help="初始学习率")
    parser.add_argument("--min-lr", type=float, default=1e-6, help="余弦退火最低学习率")
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--optimizer", default="adam", choices=["adam", "adamw", "sgd"])
    parser.add_argument("--scheduler", default="cosine", choices=["cosine", "none"])
    parser.add_argument("--warmup-epochs", type=int, default=1, help="学习率预热轮数")
    parser.add_argument("--label-smoothing", type=float, default=0.1)
    parser.add_argument("--dropout", type=float, default=0.0, help="全连接层前的 dropout 概率")
    parser.add_argument("--no-pretrained", action="store_true", help="不使用 ImageNet 预训练权重")
    parser.add_argument("--class-weight", action="store_true", default=True, help="按类别频率加权损失（默认开启）")
    parser.add_argument("--no-class-weight", action="store_false", dest="class_weight", help="关闭类别加权损失")
    parser.add_argument("--weighted-sampler", action="store_true", help="使用加权采样处理类别不平衡")
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patience", type=int, default=7, help="早停耐心值（<=0 关闭）")
    parser.add_argument("--stop-after", type=int, default=0, help="本次运行新训练 N 个 epoch 后保存断点并停止（0 为不限制）")
    parser.add_argument("--resume", default=None, help="断点路径，或 'auto' 表示 <save-dir>/<tag>/last.pth")
    parser.add_argument("--test-only", action="store_true", help="不训练，仅加载权重评估测试集")
    parser.add_argument("--limit", type=int, default=0, help="调试用：每个划分最多使用 N 张图片（0 为全部）")
    parser.add_argument("--resplit", action="store_true", help="忽略缓存，重新划分数据集")
    parser.add_argument("--split-file", default=None, help="数据集划分缓存文件路径")
    parser.add_argument("--device", default="auto", help="auto / cuda / cpu")
    parser.add_argument("--amp", action="store_true", default=True, help="CUDA 下启用混合精度（默认开启）")
    parser.add_argument("--no-amp", action="store_false", dest="amp", help="关闭混合精度")
    return parser.parse_args()


def estimate_remaining_seconds(history, remaining_epochs, fallback_epoch_sec=0.0):
    """根据历史每轮实际耗时（含验证）估计剩余训练时间。"""
    if remaining_epochs <= 0:
        return 0.0
    epoch_times = [row.get("train_time_sec", 0.0) + row.get("val_time_sec", 0.0) for row in history]
    epoch_times = [value for value in epoch_times if value > 0]
    average = sum(epoch_times) / len(epoch_times) if epoch_times else fallback_epoch_sec
    return average * remaining_epochs


def make_optimizer(args, model):
    if args.optimizer == "adam":
        return torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    if args.optimizer == "adamw":
        return torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    return torch.optim.SGD(
        model.parameters(), lr=args.lr, momentum=0.9, weight_decay=args.weight_decay, nesterov=True
    )


def make_scheduler(args, optimizer):
    """线性 warmup + 余弦退火（LambdaLR 实现，曲线连续且便于断点恢复）。"""
    if args.scheduler != "cosine":
        return None

    total_epochs = max(1, args.epochs)
    warmup_epochs = max(0, args.warmup_epochs)
    min_factor = min(1.0, args.min_lr / max(args.lr, 1e-12))

    def lr_lambda(current_epoch):
        if warmup_epochs > 0 and current_epoch < warmup_epochs:
            return 0.1 + 0.9 * (current_epoch / warmup_epochs)
        progress = (current_epoch - warmup_epochs) / max(1, total_epochs - warmup_epochs)
        progress = min(max(progress, 0.0), 1.0)
        cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
        return min_factor + (1.0 - min_factor) * cosine

    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


def main():
    args = parse_args()
    device = get_device(args.device)
    set_seed(args.seed)

    model_name = args.model or "resnet18"
    tag = args.tag or model_name
    run_dir = (Path(args.save_dir) / tag).resolve()
    log_dir = (Path(args.log_dir) / tag).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(log_dir / f"train_{now_str()}.log")

    logger.info("=" * 72)
    logger.info("基于深度学习的农作物病害识别 - 模型训练")
    logger.info(f"设备: {device}" + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else ""))
    logger.info(f"参数: {json.dumps(vars(args), ensure_ascii=False)}")

    # ---------------- 数据 ----------------
    data_dir = Path(args.data_dir).expanduser()
    if not data_dir.is_absolute():
        data_dir = (PROJECT_ROOT / data_dir).resolve()
    (train_samples, val_samples, test_samples), classes, split_file = load_or_create_split(
        data_dir,
        split_file=args.split_file,
        ratios=(0.7, 0.15, 0.15),
        seed=args.seed,
        resplit=args.resplit,
    )
    num_classes = len(classes)
    logger.info(f"数据集: {data_dir}")
    logger.info(f"划分文件: {split_file}")
    logger.info(
        f"样本数: 训练 {len(train_samples)} | 验证 {len(val_samples)} | 测试 {len(test_samples)} | 类别 {num_classes}"
    )

    if args.limit > 0:
        train_samples = limit_split(train_samples, args.limit, args.seed)
        val_samples = limit_split(val_samples, args.limit, args.seed)
        test_samples = limit_split(test_samples, args.limit, args.seed + 1)
        logger.info(
            f"[调试] 每个划分限制 {args.limit} 张: "
            f"训练 {len(train_samples)} | 验证 {len(val_samples)} | 测试 {len(test_samples)}"
        )

    train_loader, val_loader, test_loader = build_dataloaders(
        train_samples,
        val_samples,
        test_samples,
        root=data_dir,
        img_size=args.img_size,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        weighted_sampler=args.weighted_sampler,
        num_classes=num_classes,
    )

    # ---------------- 损失函数 ----------------
    class_weights = None
    if args.class_weight:
        weights, counts = compute_class_weights(train_samples, num_classes)
        class_weights = weights.to(device)
        logger.info(
            f"类别加权损失: 开启 | 训练集每类样本 {int(counts.min())} ~ {int(counts.max())} 张"
            f"（不平衡比 {counts.max() / max(counts.min(), 1):.1f}:1）"
        )
    if args.weighted_sampler:
        logger.info("加权采样: 开启")
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=args.label_smoothing)

    # ---------------- 模型 ----------------
    checkpoint_path = None
    if args.test_only:
        checkpoint_path = Path(args.resume) if args.resume and args.resume != "auto" else run_dir / "best.pth"
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"仅评估模式需要权重文件: {checkpoint_path}")
        state = load_checkpoint(checkpoint_path, device)
        ckpt_model = state.get("model_name")
        if args.model and ckpt_model and args.model != ckpt_model:
            raise ValueError(f"权重由 {ckpt_model} 训练，与 --model {args.model} 不一致")
        model_name = ckpt_model or model_name

    model = build_model(
        model_name,
        num_classes=num_classes,
        pretrained=not args.no_pretrained and not args.test_only,
        dropout=args.dropout,
    ).to(device)
    logger.info(f"模型: {model_name} | 可训练参数: {count_parameters(model) / 1e6:.2f} M")

    if args.test_only:
        model.load_state_dict(state["model"])
        best_acc = float(state.get("best_acc", 0.0))
        best_epoch = int(state.get("best_epoch", -1))
        logger.info(
            f"仅评估模式 | 权重: {checkpoint_path} | epoch {best_epoch + 1} | val_acc {best_acc * 100:.2f}%"
        )
        test_metrics = evaluate(model, test_loader, criterion, device, num_classes, desc="test")
        report_test(logger, test_metrics, classes, log_dir)
        return

    # ---------------- 优化器 / 调度器 / AMP ----------------
    optimizer = make_optimizer(args, model)
    scheduler = make_scheduler(args, optimizer)
    logger.info(
        f"优化器: {args.optimizer} (lr {args.lr}, wd {args.weight_decay}) | "
        f"调度器: {args.scheduler} (warmup {args.warmup_epochs} epoch) | 标签平滑: {args.label_smoothing}"
    )

    use_amp = args.amp and device.type == "cuda"
    scaler = torch.cuda.amp.GradScaler(enabled=use_amp)
    if use_amp:
        logger.info("混合精度训练 (AMP): 开启")

    # ---------------- 断点恢复 ----------------
    start_epoch = 0
    best_acc = 0.0
    best_epoch = -1
    history = []
    resume_path = None
    if args.resume:
        resume_path = run_dir / "last.pth" if args.resume == "auto" else Path(args.resume)
        if not resume_path.exists():
            if args.resume != "auto":
                raise FileNotFoundError(f"断点文件不存在: {resume_path}")
            logger.warning(f"未找到断点文件 {resume_path}（--resume auto），将从头开始训练")
            resume_path = None
    if resume_path is not None:
        state = load_checkpoint(resume_path, device)
        ckpt_model = state.get("model_name")
        if ckpt_model and ckpt_model != model_name:
            raise ValueError(f"断点由 {ckpt_model} 训练，与当前 --model {model_name} 不一致")
        if state.get("classes") and state["classes"] != classes:
            raise ValueError("断点保存的类别列表与当前数据集不一致")

        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        if scheduler is not None and state.get("scheduler"):
            scheduler.load_state_dict(state["scheduler"])
        if use_amp and state.get("scaler"):
            scaler.load_state_dict(state["scaler"])

        start_epoch = int(state.get("epoch", -1)) + 1
        best_acc = float(state.get("best_acc", 0.0))
        best_epoch = int(state.get("best_epoch", -1))
        history = list(state.get("history", []))

        old_epochs = state.get("args", {}).get("epochs")
        if old_epochs and old_epochs != args.epochs:
            logger.warning(f"断点原目标轮数为 {old_epochs}，当前为 {args.epochs}，学习率按新总轮数调度")
        logger.info(
            f"断点续训: 已加载 {resume_path}（完成 {start_epoch} epoch, 历史最优 val_acc {best_acc * 100:.2f}%）"
        )
        remaining_total = max(0, args.epochs - start_epoch)
        if remaining_total > 0:
            eta = estimate_remaining_seconds(history, remaining_total)
            if eta > 0:
                logger.info(f"剩余 {remaining_total} 个 epoch，按历史速度预计还需 {format_duration(eta)}")
        if start_epoch >= args.epochs:
            logger.info("已完成全部目标轮数，跳过训练直接评估")
    else:
        logger.info(f"开始训练: 共 {args.epochs} 个 epoch（每个 epoch 结束后保存一个断点）")

    # ---------------- 训练 ----------------
    epochs_since_improve = 0
    for epoch in range(start_epoch, args.epochs):
        lr = optimizer.param_groups[0]["lr"]
        train_metrics = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device, epoch + 1, use_amp=use_amp
        )
        val_metrics = evaluate(
            model, val_loader, criterion, device, num_classes,
            desc=f"Epoch {epoch + 1:03d} val", use_amp=use_amp,
        )
        if scheduler is not None:
            scheduler.step()

        is_best = val_metrics["accuracy"] > best_acc
        if is_best:
            best_acc = val_metrics["accuracy"]
            best_epoch = epoch
            epochs_since_improve = 0
        else:
            epochs_since_improve += 1

        history.append({
            "epoch": epoch + 1,
            "lr": round(lr, 8),
            "train_loss": round(train_metrics["loss"], 6),
            "train_acc": round(train_metrics["acc"], 6),
            "val_loss": round(val_metrics["loss"], 6),
            "val_acc": round(val_metrics["accuracy"], 6),
            "val_macro_f1": round(val_metrics["macro_f1"], 6),
            "best_val_acc": round(best_acc, 6),
            "train_time_sec": round(train_metrics["time"], 1),
            "val_time_sec": round(val_metrics["time"], 1),
        })
        write_history_csv(log_dir / "history.csv", history)

        logger.info(
            f"Epoch {epoch + 1:03d}/{args.epochs} | lr {lr:.2e} | "
            f"train loss {train_metrics['loss']:.4f} acc {train_metrics['acc'] * 100:.2f}% | "
            f"val loss {val_metrics['loss']:.4f} acc {val_metrics['accuracy'] * 100:.2f}% "
            f"macro-F1 {val_metrics['macro_f1'] * 100:.2f}%"
            + ("  [best]" if is_best else "")
        )

        state = {
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict() if scheduler is not None else None,
            "scaler": scaler.state_dict() if use_amp else None,
            "best_acc": best_acc,
            "best_epoch": best_epoch,
            "classes": classes,
            "model_name": model_name,
            "args": vars(args),
            "history": history,
        }
        save_checkpoint(run_dir / "last.pth", state)
        if is_best:
            save_checkpoint(run_dir / "best.pth", state)

        done = epoch + 1
        remaining = max(0, args.epochs - done)
        saved_files = "last.pth + best.pth" if is_best else "last.pth"
        if remaining > 0:
            eta = estimate_remaining_seconds(history, remaining)
            logger.info(
                f"[断点 {done}/{args.epochs}] 已保存 {saved_files} | "
                f"剩余 {remaining} 个 epoch，预计还需 {format_duration(eta)}"
            )
        else:
            logger.info(f"[断点 {done}/{args.epochs}] 已保存 {saved_files} | 全部轮次训练完成，开始测试集评估")

        if args.patience > 0 and epochs_since_improve >= args.patience:
            logger.info(
                f"早停: 验证准确率连续 {args.patience} 个 epoch 未提升"
                f"（最优 epoch {best_epoch + 1}, val_acc {best_acc * 100:.2f}%）"
            )
            break

        trained_this_run = epoch + 1 - start_epoch
        if args.stop_after > 0 and trained_this_run >= args.stop_after:
            logger.info(
                f"已按 --stop-after {args.stop_after} 完成本次运行的 {trained_this_run} 个 epoch"
                f"（断点 {epoch + 1}/{args.epochs} 已保存），停止训练"
            )
            break

    # ---------------- 测试集评估 ----------------
    best_path = run_dir / "best.pth"
    if best_path.exists():
        state = load_checkpoint(best_path, device)
        model.load_state_dict(state["model"])
        best_acc = float(state.get("best_acc", best_acc))
        best_epoch = int(state.get("best_epoch", best_epoch))
    else:
        best_path = run_dir / "last.pth"
    logger.info(
        f"加载最优权重 {best_path.name}（epoch {best_epoch + 1}, val_acc {best_acc * 100:.2f}%）评估测试集"
    )
    test_metrics = evaluate(model, test_loader, criterion, device, num_classes, desc="test", use_amp=use_amp)
    report_test(logger, test_metrics, classes, log_dir)
    logger.info(f"全部完成。权重目录: {run_dir} | 日志目录: {log_dir}")


if __name__ == "__main__":
    main()

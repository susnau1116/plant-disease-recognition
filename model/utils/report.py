"""评估结果报告：指标日志、CSV 与混淆矩阵图。"""

import csv
import json
from pathlib import Path

import numpy as np


def plot_confusion_matrix(cm, classes, path, logger=None):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        if logger:
            logger.warning("未安装 matplotlib，跳过混淆矩阵绘图")
        return

    figure, axis = plt.subplots(figsize=(16, 14))
    image = axis.imshow(cm, interpolation="nearest", cmap="Blues")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    axis.set_xticks(range(len(classes)))
    axis.set_yticks(range(len(classes)))
    axis.set_xticklabels(classes, rotation=90, fontsize=7)
    axis.set_yticklabels(classes, fontsize=7)
    axis.set_xlabel("Predicted")
    axis.set_ylabel("True")
    axis.set_title("Confusion Matrix")
    figure.tight_layout()
    figure.savefig(path, dpi=200)
    plt.close(figure)
    if logger:
        logger.info(f"混淆矩阵图: {path}")


def report_test(logger, metrics, classes, log_dir):
    """输出测试集指标并保存 JSON / 每类指标 CSV / 混淆矩阵。"""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.info("-" * 72)
    logger.info(f"测试集准确率: {metrics['accuracy'] * 100:.2f}%  (样本 {metrics.get('num_samples', '-')})")
    logger.info(
        f"macro    P {metrics['macro_precision'] * 100:.2f}% | "
        f"R {metrics['macro_recall'] * 100:.2f}% | F1 {metrics['macro_f1'] * 100:.2f}%"
    )
    logger.info(
        f"weighted P {metrics['weighted_precision'] * 100:.2f}% | "
        f"R {metrics['weighted_recall'] * 100:.2f}% | F1 {metrics['weighted_f1'] * 100:.2f}%"
    )

    cm = metrics["confusion_matrix"]
    np.savetxt(log_dir / "confusion_matrix.csv", cm, fmt="%d", delimiter=",")

    per_class = metrics["per_class"]
    with (log_dir / "per_class_metrics.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["class", "precision", "recall", "f1", "support"])
        for index, name in enumerate(classes):
            writer.writerow([
                name,
                f"{per_class['precision'][index]:.4f}",
                f"{per_class['recall'][index]:.4f}",
                f"{per_class['f1'][index]:.4f}",
                per_class["support"][index],
            ])

    summary = {"num_classes": len(classes), "classes": classes}
    summary.update({key: value for key, value in metrics.items() if key != "confusion_matrix"})
    (log_dir / "test_metrics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info(f"评估结果: {log_dir / 'test_metrics.json'} | per_class_metrics.csv | confusion_matrix.csv")
    plot_confusion_matrix(cm, classes, log_dir / "confusion_matrix.png", logger)

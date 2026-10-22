"""分类指标计算（纯 numpy 实现，不依赖 scikit-learn）。

包含：准确率、精确率、召回率、F1、混淆矩阵（含 macro / weighted 汇总）。
"""

import numpy as np


def accuracy(labels, preds) -> float:
    labels = np.asarray(labels)
    preds = np.asarray(preds)
    if labels.size == 0:
        return 0.0
    return float((labels == preds).mean())


def confusion_matrix(labels, preds, num_classes: int) -> np.ndarray:
    labels = np.asarray(labels, dtype=np.int64).ravel()
    preds = np.asarray(preds, dtype=np.int64).ravel()
    if labels.size == 0:
        return np.zeros((num_classes, num_classes), dtype=np.int64)
    index = labels * num_classes + preds
    counts = np.bincount(index, minlength=num_classes * num_classes)
    return counts.reshape(num_classes, num_classes).astype(np.int64)


def per_class_prf(cm: np.ndarray):
    """由混淆矩阵计算每类的 precision / recall / f1 / support。"""
    cm = cm.astype(np.float64)
    tp = np.diag(cm)
    fp = cm.sum(axis=0) - tp
    fn = cm.sum(axis=1) - tp
    support = cm.sum(axis=1)

    precision = np.divide(tp, tp + fp, out=np.zeros_like(tp), where=(tp + fp) > 0)
    recall = np.divide(tp, tp + fn, out=np.zeros_like(tp), where=(tp + fn) > 0)
    denominator = precision + recall
    f1 = np.divide(2.0 * precision * recall, denominator, out=np.zeros_like(tp), where=denominator > 0)
    return precision, recall, f1, support


def compute_metrics(labels, preds, num_classes: int) -> dict:
    cm = confusion_matrix(labels, preds, num_classes)
    precision, recall, f1, support = per_class_prf(cm)

    support_sum = float(support.sum())
    if support_sum > 0:
        weighted_precision = float((precision * support).sum() / support_sum)
        weighted_recall = float((recall * support).sum() / support_sum)
        weighted_f1 = float((f1 * support).sum() / support_sum)
    else:
        weighted_precision = weighted_recall = weighted_f1 = 0.0

    return {
        "accuracy": accuracy(labels, preds),
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": float(f1.mean()),
        "weighted_precision": weighted_precision,
        "weighted_recall": weighted_recall,
        "weighted_f1": weighted_f1,
        "confusion_matrix": cm,
        "per_class": {
            "precision": precision.tolist(),
            "recall": recall.tolist(),
            "f1": f1.tolist(),
            "support": support.astype(np.int64).tolist(),
        },
    }

# -*- coding: utf-8 -*-
"""Generate per-model shape flow diagrams for docs/模型介绍.md."""
import os
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager

OUT = str(Path(__file__).resolve().parent / "assets")
os.makedirs(OUT, exist_ok=True)

for cand in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC"]:
    if any(f.name == cand for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [cand]
        break
plt.rcParams["axes.unicode_minus"] = False

COLORS = {
    "input": ("#f1f5f9", "#94a3b8"),
    "conv": ("#dbeafe", "#60a5fa"),
    "pool": ("#fef3c7", "#f59e0b"),
    "block": ("#e0e7ff", "#6366f1"),
    "head": ("#dcfce7", "#22c55e"),
    "output": ("#fce7f3", "#ec4899"),
    "special": ("#fee2e2", "#ef4444"),
}


def draw_flow(title, subtitle, steps, path, footer=None):
    n = len(steps)
    fig_h = 1.05 + n * 0.74
    fig, ax = plt.subplots(figsize=(7.2, fig_h))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.992, title, ha="center", va="top", fontsize=15, fontweight="bold")
    if subtitle:
        ax.text(0.5, 0.958, subtitle, ha="center", va="top", fontsize=9.4, color="#475569")

    top, bottom = 0.895, (0.085 if footer else 0.035)
    step = (top - bottom) / n
    box_h = step * 0.70
    x0, w = 0.08, 0.84

    for i, s in enumerate(steps):
        y_top = top - i * step
        fc, ec = COLORS[s.get("color", "conv")]
        ax.add_patch(FancyBboxPatch(
            (x0, y_top - box_h), w, box_h,
            boxstyle="round,pad=0.003,rounding_size=0.010",
            facecolor=fc, edgecolor=ec, linewidth=1.4,
        ))
        label, shape = s["label"], s.get("shape", "")
        if shape:
            ax.text(x0 + w / 2, y_top - box_h * 0.37, label, ha="center", va="center", fontsize=10.5)
            ax.text(x0 + w / 2, y_top - box_h * 0.75, shape, ha="center", va="center",
                    fontsize=9, color="#334155")
        else:
            ax.text(x0 + w / 2, y_top - box_h / 2, label, ha="center", va="center", fontsize=10.5)
        if i < n - 1:
            ax.add_patch(FancyArrowPatch(
                (0.5, y_top - box_h), (0.5, y_top - step),
                arrowstyle="-|>", mutation_scale=13, color="#64748b", linewidth=1.2,
            ))

    if footer:
        ax.text(0.5, 0.018, footer, ha="center", va="bottom", fontsize=8.6, color="#475569")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.995, bottom=0.005)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)
    print("saved", os.path.basename(path))


def draw_blocks():
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 5.0))
    titles = ["BasicBlock（ResNet18/34）", "Bottleneck（ResNet50）", "倒残差块（MobileNetV2）"]
    steps = [
        ["输入 x（64×56×56）", "3×3 卷积 → BN → ReLU", "3×3 卷积 → BN", "逐元素相加  F(x)+x", "ReLU → 输出"],
        ["输入 x（256×56×56）", "1×1 卷积：256 → 64（降维）", "3×3 卷积：64 → 64", "1×1 卷积：64 → 256（升维）", "相加  F(x)+x（1×1 匹配）", "输出 256×56×56"],
        ["输入 x（24×56×56）", "1×1 卷积：24 → 144（×6，ReLU6）", "3×3 深度卷积：144 通道", "1×1 卷积：144 → 24（线性）", "相加（形状相同才加）", "输出 24×56×56"],
    ]
    colors = [
        ["input", "conv", "conv", "block", "head"],
        ["input", "conv", "conv", "conv", "block", "head"],
        ["input", "conv", "conv", "conv", "block", "head"],
    ]
    for ax, title, labels, cols in zip(axes, titles, steps, colors):
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
        ax.set_title(title, fontsize=11.5, fontweight="bold", pad=10)
        n = len(labels)
        top, bottom = 0.84, 0.05
        step = (top - bottom) / n
        box_h = step * 0.66
        for i, (lab, col) in enumerate(zip(labels, cols)):
            y_top = top - i * step
            fc, ec = COLORS[col]
            ax.add_patch(FancyBboxPatch((0.20, y_top - box_h), 0.66, box_h,
                                        boxstyle="round,pad=0.004,rounding_size=0.02",
                                        facecolor=fc, edgecolor=ec, linewidth=1.2))
            ax.text(0.53, y_top - box_h / 2, lab, ha="center", va="center", fontsize=8.8)
            if i < n - 1:
                ax.add_patch(FancyArrowPatch((0.53, y_top - box_h), (0.53, y_top - step),
                                             arrowstyle="-|>", mutation_scale=10,
                                             color="#64748b", linewidth=1.0))
        # shortcut on the left for the residual blocks
        if "BasicBlock" in title or "Bottleneck" in title or "倒残差" in title:
            y_from = top - box_h / 2
            y_to = top - (n - 2) * step - box_h / 2
            ax.plot([0.20, 0.08, 0.08, 0.20], [y_from, y_from, y_to, y_to],
                    color="#ef4444", linewidth=1.1, solid_capstyle="round")
            ax.annotate("", xy=(0.20, y_to), xytext=(0.10, y_to),
                        arrowprops=dict(arrowstyle="-|>", color="#ef4444", lw=1.1))
            ax.text(0.065, (y_from + y_to) / 2, "捷径", rotation=90, fontsize=8,
                    color="#ef4444", ha="center", va="center")

    fig.suptitle("三种核心模块的内部计算", fontsize=14, fontweight="bold", y=0.995)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.85, bottom=0.02, wspace=0.12)
    path = os.path.join(OUT, "blocks_internal.png")
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)
    print("saved", os.path.basename(path))


draw_blocks()

draw_flow(
    "所有深度模型共用的输入管线",
    "训练 / 评估 / 在线推理三处完全一致（尺寸、顺序、均值方差都相同）",
    [
        {"label": "上传图片（JPG / PNG / BMP / WEBP）", "shape": "任意尺寸，≤10 MB", "color": "input"},
        {"label": "PIL 解码 → RGB（JPEG 先 draft 降到 ~512）", "shape": "H×W×3 uint8", "color": "conv"},
        {"label": "Resize：短边 → 256，长边等比", "shape": "256×341×3（示例）", "color": "conv"},
        {"label": "CenterCrop 224×224", "shape": "224×224×3", "color": "conv"},
        {"label": "ToTensor + 除以 255", "shape": "3×224×224 float32", "color": "block"},
        {"label": "Normalize（ImageNet 均值/标准差）", "shape": "3×224×224 标准化", "color": "block"},
        {"label": "增加 batch 维", "shape": "1×3×224×224", "color": "head"},
    ],
    os.path.join(OUT, "input_pipeline.png"),
    footer="均值 (0.485, 0.456, 0.406)　标准差 (0.229, 0.224, 0.225)",
)

draw_flow(
    "ResNet18 逐层 shape 流程",
    "输入 1×3×224×224 → 38 类 logit（11.20 M 参数，42.7 MB，CPU 9.7 ms/张）",
    [
        {"label": "输入图像", "shape": "3×224×224", "color": "input"},
        {"label": "conv1：7×7 / stride 2，64 通道 + BN + ReLU", "shape": "64×112×112", "color": "conv"},
        {"label": "maxpool：3×3 / stride 2", "shape": "64×56×56", "color": "pool"},
        {"label": "layer1：2 × BasicBlock（64）", "shape": "64×56×56", "color": "block"},
        {"label": "layer2：2 × BasicBlock（128，首块 s=2）", "shape": "128×28×28", "color": "block"},
        {"label": "layer3：2 × BasicBlock（256，首块 s=2）", "shape": "256×14×14", "color": "block"},
        {"label": "layer4：2 × BasicBlock（512，首块 s=2）", "shape": "512×7×7", "color": "block"},
        {"label": "全局平均池化 GAP", "shape": "512", "color": "pool"},
        {"label": "fc：Linear(512, 38)", "shape": "38（logit）", "color": "head"},
        {"label": "softmax → Top-5（后端完成）", "shape": "38 个概率", "color": "output"},
    ],
    os.path.join(OUT, "model_resnet18.png"),
    footer="每个 stage 第一块用 1×1 卷积 + BN 调整通道，其余块为恒等捷径",
)

draw_flow(
    "ResNet34 逐层 shape 流程",
    "与 ResNet18 同构，仅四个 stage 的块数不同（21.30 M 参数，81.3 MB，CPU 20.9 ms/张）",
    [
        {"label": "输入图像", "shape": "3×224×224", "color": "input"},
        {"label": "conv1：7×7 / stride 2，64 通道 + BN + ReLU", "shape": "64×112×112", "color": "conv"},
        {"label": "maxpool：3×3 / stride 2", "shape": "64×56×56", "color": "pool"},
        {"label": "layer1：3 × BasicBlock（64）", "shape": "64×56×56", "color": "block"},
        {"label": "layer2：4 × BasicBlock（128，首块 s=2）", "shape": "128×28×28", "color": "block"},
        {"label": "layer3：6 × BasicBlock（256，首块 s=2）", "shape": "256×14×14", "color": "block"},
        {"label": "layer4：3 × BasicBlock（512，首块 s=2）", "shape": "512×7×7", "color": "block"},
        {"label": "全局平均池化 GAP", "shape": "512", "color": "pool"},
        {"label": "fc：Linear(512, 38)", "shape": "38（logit）", "color": "head"},
        {"label": "softmax → Top-5（后端完成）", "shape": "38 个概率", "color": "output"},
    ],
    os.path.join(OUT, "model_resnet34.png"),
    footer="块数 [3,4,6,3]，比 ResNet18 多 10 个 BasicBlock",
)

draw_flow(
    "ResNet50 逐层 shape 流程",
    "输入 1×3×224×224 → 38 类 logit（23.59 M 参数，89.9 MB，CPU 23.0 ms/张）",
    [
        {"label": "输入图像", "shape": "3×224×224", "color": "input"},
        {"label": "conv1：7×7 / stride 2，64 通道 + BN + ReLU", "shape": "64×112×112", "color": "conv"},
        {"label": "maxpool：3×3 / stride 2", "shape": "64×56×56", "color": "pool"},
        {"label": "layer1：3 × Bottleneck（64→256）", "shape": "256×56×56", "color": "block"},
        {"label": "layer2：4 × Bottleneck（128→512，首块 s=2）", "shape": "512×28×28", "color": "block"},
        {"label": "layer3：6 × Bottleneck（256→1024，首块 s=2）", "shape": "1024×14×14", "color": "block"},
        {"label": "layer4：3 × Bottleneck（512→2048，首块 s=2）", "shape": "2048×7×7", "color": "block"},
        {"label": "全局平均池化 GAP", "shape": "2048", "color": "pool"},
        {"label": "fc：Linear(2048, 38)", "shape": "38（logit）", "color": "head"},
        {"label": "softmax → Top-5（后端完成）", "shape": "38 个概率", "color": "output"},
    ],
    os.path.join(OUT, "model_resnet50.png"),
    footer="Bottleneck 内部为 1×1 降维 → 3×3 → 1×1 升维（×4）",
)

draw_flow(
    "AlexNet 逐层 shape 流程（本项目改造版）",
    "卷积部分保持原版，分类头换成单层 Linear(9216, 38)（2.82 M 参数，10.8 MB，CPU 3.7 ms/张）",
    [
        {"label": "输入图像", "shape": "3×224×224", "color": "input"},
        {"label": "conv1：11×11 / stride 4，64 通道 + ReLU", "shape": "64×55×55", "color": "conv"},
        {"label": "maxpool 3×3 / stride 2", "shape": "64×27×27", "color": "pool"},
        {"label": "conv2：5×5，192 通道 + ReLU", "shape": "192×27×27", "color": "conv"},
        {"label": "maxpool 3×3 / stride 2", "shape": "192×13×13", "color": "pool"},
        {"label": "conv3：3×3，384 通道 + ReLU", "shape": "384×13×13", "color": "conv"},
        {"label": "conv4：3×3，256 通道 + ReLU", "shape": "256×13×13", "color": "conv"},
        {"label": "conv5：3×3，256 通道 + ReLU", "shape": "256×13×13", "color": "conv"},
        {"label": "maxpool 3×3 / stride 2", "shape": "256×6×6", "color": "pool"},
        {"label": "展平（原版为 4096→4096→1000 三层）", "shape": "9216", "color": "special"},
        {"label": "fc：Linear(9216, 38)", "shape": "38（logit）", "color": "head"},
        {"label": "softmax → Top-5（后端完成）", "shape": "38 个概率", "color": "output"},
    ],
    os.path.join(OUT, "model_alexnet.png"),
    footer="原版分类头 58.6 M 参数，替换后总参数从 61.1 M 降到 2.82 M；无 BatchNorm，学习率需降到 1e-4",
)

draw_flow(
    "MobileNetV2 逐层 shape 流程",
    "初始卷积 + 17 个倒残差块 + 1×1 升维（2.27 M 参数，8.6 MB，CPU 2.9 ms/张）",
    [
        {"label": "输入图像", "shape": "3×224×224", "color": "input"},
        {"label": "conv 3×3 / stride 2，32 通道 + BN + ReLU6", "shape": "32×112×112", "color": "conv"},
        {"label": "bneck ×1：t=1，16 通道", "shape": "16×112×112", "color": "block"},
        {"label": "bneck ×2：t=6，24 通道，首块 s=2", "shape": "24×56×56", "color": "block"},
        {"label": "bneck ×3：t=6，32 通道，首块 s=2", "shape": "32×28×28", "color": "block"},
        {"label": "bneck ×4：t=6，64 通道，首块 s=2", "shape": "64×14×14", "color": "block"},
        {"label": "bneck ×3：t=6，96 通道", "shape": "96×14×14", "color": "block"},
        {"label": "bneck ×3：t=6，160 通道，首块 s=2", "shape": "160×7×7", "color": "block"},
        {"label": "bneck ×1：t=6，320 通道", "shape": "320×7×7", "color": "block"},
        {"label": "conv 1×1，320→1280 + BN + ReLU6", "shape": "1280×7×7", "color": "conv"},
        {"label": "全局平均池化 GAP", "shape": "1280", "color": "pool"},
        {"label": "Dropout(0.2) → Linear(1280, 38)", "shape": "38（logit）", "color": "head"},
        {"label": "softmax → Top-5（后端完成）", "shape": "38 个概率", "color": "output"},
    ],
    os.path.join(OUT, "model_mobilenetv2.png"),
    footer="倒残差块：1×1 扩张（ReLU6）→ 3×3 深度卷积（ReLU6）→ 1×1 投影（无激活）→ 相加",
)

draw_flow(
    "MobileNetV3-Large 逐层 shape 流程",
    "初始卷积 + 15 个 bneck（含 SE / h-swish）+ 1×1 升维（4.25 M 参数，16.2 MB，CPU 2.9 ms/张）",
    [
        {"label": "输入图像", "shape": "3×224×224", "color": "input"},
        {"label": "conv 3×3 / stride 2，16 通道 + BN + h-swish", "shape": "16×112×112", "color": "conv"},
        {"label": "bneck ×3：16→16 / 24 / 24", "shape": "24×56×56", "color": "block"},
        {"label": "bneck ×3：40 通道（含 SE），首块 s=2", "shape": "40×28×28", "color": "block"},
        {"label": "bneck ×4：80 通道", "shape": "80×14×14", "color": "block"},
        {"label": "bneck ×2：112 通道（含 SE）", "shape": "112×14×14", "color": "block"},
        {"label": "bneck ×3：160 通道（含 SE），首块 s=2", "shape": "160×7×7", "color": "block"},
        {"label": "conv 1×1，160→960 + BN + h-swish", "shape": "960×7×7", "color": "conv"},
        {"label": "全局平均池化 GAP", "shape": "960", "color": "pool"},
        {"label": "Linear(960, 1280) + Hardswish", "shape": "1280", "color": "conv"},
        {"label": "Dropout(0.2) → Linear(1280, 38)", "shape": "38（logit）", "color": "head"},
        {"label": "softmax → Top-5（后端完成）", "shape": "38 个概率", "color": "output"},
    ],
    os.path.join(OUT, "model_mobilenetv3.png"),
    footer="SE：全局池化 → 两层全连接学通道权重 → 逐通道相乘；h-swish(x)=x·ReLU6(x+3)/6",
)


def draw_traditional():
    fig, ax = plt.subplots(figsize=(11.0, 6.0))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.5, 0.975, "传统机器学习路线：512 维深度特征 + 5 种分类器",
            ha="center", va="top", fontsize=14, fontweight="bold")

    def box(x, y, w, h, text, color="conv", fs=9.5):
        fc, ec = COLORS[color]
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.02",
                                    facecolor=fc, edgecolor=ec, linewidth=1.2))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)

    def arr(x1, y1, x2, y2, style="-|>"):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=12,
                                     color="#64748b", linewidth=1.2))

    box(0.03, 0.70, 0.17, 0.15, "叶片图像\n224×224×3", "input")
    box(0.23, 0.70, 0.18, 0.15, "ResNet18 骨干\n（去掉 fc）", "conv")
    box(0.44, 0.70, 0.15, 0.15, "GAP\n512 维特征", "pool")
    box(0.62, 0.70, 0.17, 0.15, "StandardScaler\n（树模型跳过）", "special")
    arr(0.20, 0.775, 0.23, 0.775)
    arr(0.41, 0.775, 0.44, 0.775)
    arr(0.59, 0.775, 0.62, 0.775)

    items = [
        ("线性 SVM\n38 个超平面取最大", "#dbeafe"),
        ("SVM-RBF\n703 个二分类器投票", "#ede9fe"),
        ("KNN（k=5）\n30,412 个距离取最近", "#fef3c7"),
        ("决策树\n按阈值走到叶子", "#dcfce7"),
        ("随机森林\n300 棵树投票", "#fee2e2"),
    ]
    centers = []
    for i, (text, color) in enumerate(items):
        x, w = 0.03 + i * 0.194, 0.175
        ax.add_patch(FancyBboxPatch((x, 0.28), w, 0.19,
                                    boxstyle="round,pad=0.006,rounding_size=0.02",
                                    facecolor=color, edgecolor="#94a3b8", linewidth=1.0))
        ax.text(x + w / 2, 0.375, text, ha="center", va="center", fontsize=8.8)
        centers.append(x + w / 2)
        arr(0.705, 0.70, x + w / 2, 0.475)

    ax.plot([0.09, 0.93], [0.215, 0.215], color="#64748b", linewidth=1.2)
    for c in centers:
        arr(c, 0.28, c, 0.215, style="-")
    box(0.34, 0.05, 0.32, 0.09, "输出：预测类别（取最大分数 / 多数投票）", "head", fs=9.5)
    arr(0.5, 0.215, 0.5, 0.14)

    ax.text(0.5, 0.015, "两轮实验只换特征来源：ImageNet 预训练特征 vs 本项目微调特征",
            ha="center", va="bottom", fontsize=8.8, color="#475569")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.99, bottom=0.02)
    path = os.path.join(OUT, "traditional_ml.png")
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)
    print("saved", os.path.basename(path))


draw_traditional()

"""模型库：ResNet / AlexNet / MobileNet 等 torchvision 分类网络的迁移学习封装。

统一替换分类头为项目类别数，供训练（train.py）、导出（export_onnx.py）、
特征提取（train_ml.py）共用。

注意：首次使用某个结构时会自动下载 ImageNet 预训练权重
（ResNet18 约 45MB、MobileNetV2 约 14MB、AlexNet 约 233MB）。
"""

import warnings

import torch.nn as nn
from torchvision import models

MODEL_ZOO = {
    "resnet18": (models.resnet18, models.ResNet18_Weights.IMAGENET1K_V1),
    "resnet34": (models.resnet34, models.ResNet34_Weights.IMAGENET1K_V1),
    "resnet50": (models.resnet50, models.ResNet50_Weights.IMAGENET1K_V1),
    "alexnet": (models.alexnet, models.AlexNet_Weights.IMAGENET1K_V1),
    "mobilenet_v2": (models.mobilenet_v2, models.MobileNet_V2_Weights.IMAGENET1K_V1),
    "mobilenet_v3_large": (models.mobilenet_v3_large, models.MobileNet_V3_Large_Weights.IMAGENET1K_V1),
}


def _make_head(in_features: int, num_classes: int, dropout: float) -> nn.Module:
    if dropout and dropout > 0:
        return nn.Sequential(nn.Dropout(p=dropout), nn.Linear(in_features, num_classes))
    return nn.Linear(in_features, num_classes)


def _replace_head(model: nn.Module, name: str, num_classes: int, dropout: float) -> nn.Module:
    if name.startswith("alexnet"):
        # AlexNet 原分类头含两层 4096 维全连接，替换为单层以大幅减少参数量
        first_linear = next(m for m in model.classifier if isinstance(m, nn.Linear))
        model.classifier = _make_head(first_linear.in_features, num_classes, dropout)
        return model

    # ResNet 的 fc、MobileNet 的 classifier 末层等：替换最后一个全连接层
    last_name, last_module = None, None
    for module_name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            last_name, last_module = module_name, module
    if last_module is None:
        raise ValueError(f"未找到 {name} 的全连接分类层")

    parent_path, _, attribute = last_name.rpartition(".")
    parent = model.get_submodule(parent_path) if parent_path else model
    setattr(parent, attribute, _make_head(last_module.in_features, num_classes, dropout))
    return model


def build_model(name: str = "resnet18", num_classes: int = 38, pretrained: bool = True, dropout: float = 0.0):
    """构建分类模型，替换分类头为 num_classes 输出。"""
    if name not in MODEL_ZOO:
        raise ValueError(f"不支持的模型: {name}，可选: {list(MODEL_ZOO)}")

    factory, weights = MODEL_ZOO[name]
    if pretrained:
        try:
            model = factory(weights=weights)
        except Exception as exc:  # 无网络 / 下载失败时回退为从头训练
            warnings.warn(f"加载 ImageNet 预训练权重失败（{exc}），将从头训练")
            model = factory(weights=None)
    else:
        model = factory(weights=None)

    return _replace_head(model, name, num_classes, dropout)


def build_backbone(name: str = "resnet18", pretrained: bool = True) -> nn.Module:
    """构建特征提取骨干网络（去掉分类头，输出经全局平均池化）。"""
    model = build_model(name, num_classes=1000, pretrained=pretrained)
    return nn.Sequential(*list(model.children())[:-1])

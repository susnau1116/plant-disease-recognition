"""数据增强策略。

训练：随机裁剪缩放、水平/垂直翻转、随机旋转、色彩抖动、
      高斯模糊、高斯噪声、随机擦除（模拟遮挡）。
验证/测试：等比缩放 + 中心裁剪。
"""

import random

import torch
from torchvision import transforms

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class AddGaussianNoise:
    """以一定概率给归一化后的张量叠加高斯噪声，模拟田间拍摄噪声。"""

    def __init__(self, mean: float = 0.0, std: float = 0.02, p: float = 0.15):
        self.mean = mean
        self.std = std
        self.p = p

    def __call__(self, tensor: torch.Tensor) -> torch.Tensor:
        if random.random() < self.p:
            noise = torch.randn_like(tensor) * self.std + self.mean
            return tensor + noise
        return tensor

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mean={self.mean}, std={self.std}, p={self.p})"


def build_train_transform(img_size: int = 224) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.RandomResizedCrop(img_size, scale=(0.6, 1.0), ratio=(0.75, 1.333)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.5),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.25, hue=0.05),
            transforms.RandomApply([transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 1.5))], p=0.2),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
            AddGaussianNoise(std=0.02, p=0.15),
            transforms.RandomErasing(p=0.25, scale=(0.02, 0.15), ratio=(0.3, 3.3)),
        ]
    )


def build_eval_transform(img_size: int = 224, resize: int = 256) -> transforms.Compose:
    return transforms.Compose(
        [
            transforms.Resize(resize),
            transforms.CenterCrop(img_size),
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )

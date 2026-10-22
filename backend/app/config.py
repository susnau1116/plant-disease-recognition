"""后端配置：路径、模型参数与推理预处理常量。

预处理必须与训练/评估阶段一致（见 model/train.py 的验证变换）：
PIL 读图 → RGB → Resize(256, 短边) → CenterCrop(224) → ToTensor → ImageNet 归一化。
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.environ.get("CROP_DB_PATH", BASE_DIR / "database" / "app.db"))
MODEL_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"
EXAMPLES_DIR = STATIC_DIR / "examples"  # 各病害类别的典型例图（2~3 张/类）
CLASSES_FILE = MODEL_DIR / "classes.txt"
DEFAULT_MODEL = MODEL_DIR / "resnet18.onnx"
QUANTIZED_MODEL = MODEL_DIR / "resnet18_quantized.onnx"

# 默认使用 FP32 模型（本机 CPU 上更快且精度更高）；设置环境变量 CROP_MODEL=quantized 切换量化模型
MODEL_PATH = QUANTIZED_MODEL if os.environ.get("CROP_MODEL", "").lower() == "quantized" else DEFAULT_MODEL

IMG_SIZE = 224
RESIZE_SIZE = 256
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
TOP_K = 5
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# 性能相关（可用环境变量覆盖）
ORT_NUM_THREADS = int(
    os.environ.get("CROP_ORT_THREADS", str(min(8, os.cpu_count() or 4)))
)
MAX_CONCURRENT_INFERENCE = max(1, int(os.environ.get("CROP_MAX_CONCURRENT_INFERENCE", "2")))
# 大尺寸 JPEG 在解码阶段按 draft 降采样，减少手机原图的解码开销
JPEG_DRAFT_MIN_SIZE = int(os.environ.get("CROP_JPEG_DRAFT_MIN_SIZE", "1024"))
JPEG_DRAFT_TARGET = 512
# 静态例图与静态知识库的浏览器缓存时间（秒）
CACHE_MAX_AGE_STATIC = 24 * 60 * 60
CACHE_MAX_AGE_KNOWLEDGE = 5 * 60
KNOWLEDGE_ETAG = 'W/"crop-knowledge-38-v1"'


def load_classes():
    """读取训练时的类别顺序（classes.txt，每行一个 class_name）。"""
    if not CLASSES_FILE.exists():
        raise FileNotFoundError(f"类别文件不存在: {CLASSES_FILE}")
    with open(CLASSES_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

"""ONNX 推理服务。

预处理与训练/评估阶段一致（torchvision 等价实现，避免后端依赖 torch）：
1. PIL 读图并转 RGB（大尺寸 JPEG 会先用 draft 降低解码分辨率）
2. Resize(256)：短边缩放到 256，长边等比缩放
3. CenterCrop(224)
4. ToTensor：HWC uint8 → CHW float32 / 255
5. ImageNet 归一化：mean (0.485, 0.456, 0.406)，std (0.229, 0.224, 0.225)
6. softmax 输出置信度，按类别文件顺序映射
"""

import io
import threading
import time

import numpy as np
import onnxruntime as ort
from PIL import Image, UnidentifiedImageError

from .. import config

_MEAN = np.asarray(config.IMAGENET_MEAN, dtype=np.float32).reshape(1, 1, 3)
_STD = np.asarray(config.IMAGENET_STD, dtype=np.float32).reshape(1, 1, 3)
_INV_255 = np.float32(1.0 / 255.0)


class InvalidImageError(ValueError):
    """上传内容不是可解析的图片。"""


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max(axis=1, keepdims=True)
    exp = np.exp(x)
    return exp / exp.sum(axis=1, keepdims=True)


def preprocess(image_bytes: bytes, use_draft: bool | None = None) -> np.ndarray:
    """字节流 → 归一化后的 NCHW float32 张量（batch=1）。

    只解码一次；大尺寸 JPEG 用 draft 在解码阶段降采样，降低手机原图
    的解码开销。后续 Resize(256) → CenterCrop(224) 与训练保持一致。
    """
    if use_draft is None:
        use_draft = config.JPEG_DRAFT_MIN_SIZE > 0
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if use_draft and img.format == "JPEG":
                w, h = img.size
                if min(w, h) > config.JPEG_DRAFT_MIN_SIZE:
                    img.draft(
                        "RGB", (config.JPEG_DRAFT_TARGET, config.JPEG_DRAFT_TARGET)
                    )
            img = img.convert("RGB")
            w, h = img.size
            scale = config.RESIZE_SIZE / min(w, h)
            new_w, new_h = int(round(w * scale)), int(round(h * scale))
            img = img.resize((new_w, new_h), Image.BILINEAR)

            left = (new_w - config.IMG_SIZE) // 2
            top = (new_h - config.IMG_SIZE) // 2
            img = img.crop((left, top, left + config.IMG_SIZE, top + config.IMG_SIZE))

            arr = np.asarray(img, dtype=np.float32)  # HWC
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as exc:
        raise InvalidImageError("无法解析图片，请上传有效的图片文件") from exc

    # 原地归一化，避免多次生成临时数组
    arr *= _INV_255
    arr -= _MEAN
    arr /= _STD
    arr = np.transpose(arr, (2, 0, 1))  # CHW
    return np.ascontiguousarray(arr[None, ...])


class Predictor:
    """线程安全的 ONNX Runtime 推理封装（懒加载单例）。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._session = None
        self._classes = None
        self._input_name = None

    def load(self):
        if self._session is not None:
            return
        with self._lock:
            if self._session is not None:
                return
            if not config.MODEL_PATH.exists():
                raise FileNotFoundError(f"ONNX 模型不存在: {config.MODEL_PATH}")
            so = ort.SessionOptions()
            so.intra_op_num_threads = config.ORT_NUM_THREADS
            so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            session = ort.InferenceSession(
                str(config.MODEL_PATH), sess_options=so, providers=["CPUExecutionProvider"]
            )
            self._session = session
            self._classes = config.load_classes()
            self._input_name = session.get_inputs()[0].name
            # 启动时先跑一次，避免首个真实请求承担图优化/内存分配开销
            warmup = np.zeros(
                (1, 3, config.IMG_SIZE, config.IMG_SIZE), dtype=np.float32
            )
            session.run(None, {self._input_name: warmup})

    @property
    def model_name(self) -> str:
        return config.MODEL_PATH.name

    @property
    def classes(self):
        self.load()
        return self._classes

    def predict(self, image_bytes: bytes, top_k: int = config.TOP_K):
        """返回 (topk 列表, 推理耗时 ms)。每项为 (class_index, confidence)。"""
        self.load()
        tensor = preprocess(image_bytes)
        t0 = time.perf_counter()
        logits = self._session.run(None, {self._input_name: tensor})[0]
        elapsed_ms = (time.perf_counter() - t0) * 1000
        probs = softmax(np.asarray(logits))[0]
        order = np.argsort(probs)[::-1][:top_k]
        return [(int(i), float(probs[i])) for i in order], elapsed_ms


predictor = Predictor()

"""例图挑选：从 PlantVillage 数据集中为每个类别挑选典型例图。

用法（在 backend 目录下执行）：
    python scripts/select_examples.py                 # 默认 ../PlantVillage，每类 3 张
    python scripts/select_examples.py --count 2       # 每类 2 张
    python scripts/select_examples.py --source D:/PlantVillage

挑选规则：类别目录内按文件名排序后等距取 count 张（确定性、可复现），
拷贝到 backend/static/examples/<class_name>/1.jpg，供知识库详情页展示。
"""

import argparse
import shutil
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import config  # noqa: E402


def pick_images(files, count):
    """按文件名排序后等距抽取，保证覆盖首、中、尾且结果确定。"""
    if count <= 1 or len(files) <= count:
        return files[:count]
    step = (len(files) - 1) / (count - 1)
    indices = sorted({round(i * step) for i in range(count)})
    return [files[i] for i in indices]


def select_for_class(src_dir: Path, dst_dir: Path, count: int) -> int:
    files = sorted(
        p for p in src_dir.iterdir() if p.is_file() and p.suffix.lower() in config.ALLOWED_SUFFIXES
    )
    if not files:
        return 0
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True)
    picked = pick_images(files, count)
    for i, src in enumerate(picked, 1):
        shutil.copy2(src, dst_dir / f"{i}{src.suffix.lower()}")
    return len(picked)


def main():
    parser = argparse.ArgumentParser(description="从 PlantVillage 挑选每类典型例图")
    parser.add_argument(
        "--source",
        default=str(BACKEND_DIR.parent / "PlantVillage"),
        help="PlantVillage 数据集根目录（默认 backend 同级目录）",
    )
    parser.add_argument("--count", type=int, default=3, help="每类挑选张数（默认 3）")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_dir():
        raise SystemExit(f"数据集目录不存在: {source}")

    classes = config.load_classes()
    total = 0
    missing = []
    for class_name in classes:
        src_dir = source / class_name
        if not src_dir.is_dir():
            missing.append(class_name)
            continue
        total += select_for_class(src_dir, config.EXAMPLES_DIR / class_name, args.count)

    if missing:
        raise SystemExit(f"以下类别在数据集中缺失：{missing}")

    print(
        f"例图挑选完成：{len(classes)} 类 / 共 {total} 张 → {config.EXAMPLES_DIR}"
    )


if __name__ == "__main__":
    main()

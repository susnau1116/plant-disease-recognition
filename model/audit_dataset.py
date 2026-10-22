"""数据集质量审计：精确/近似重复、模糊、损坏与跨类/跨划分泄漏。

只读审计，不修改 PlantVillage 原图与固定划分文件；结果输出到
model/logs/data_audit/（summary.json + CSV）。

重复判定：
- 精确重复：文件 SHA256 相同。
- 近似重复：先按 64 位 dHash（汉明距离 <= 6）取候选，再用 64x64 灰度
  归一化互相关（NCC）复核，仅保留 NCC >= ncc_threshold 的对，避免把
  构图相似的不同叶片误判为重复。

模糊判定：
- blur_variance 为 256x256 灰度图的 Laplacian 方差；
- < blur-threshold 记为“确认模糊”，blur-threshold ~ review-threshold
  记为“待复核”（低纹理健康叶片可能得分偏低）。

用法：
    python model/audit_dataset.py
    python model/audit_dataset.py --limit 2000      # 抽样快速检查
    python model/audit_dataset.py --workers 8 --blur-threshold 30
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SPLITS = BASE_DIR / "data" / "splits" / "plantvillage_r70_15_15_seed42.json"
DEFAULT_OUT = BASE_DIR / "logs" / "data_audit"

NEAR_BANDS = 4
BAND_BITS = 16
DHASH_MAX = 6
BUCKET_CAP = 500


def _dhash(gray: Image.Image) -> int:
    small = gray.resize((9, 8), Image.Resampling.LANCZOS)
    arr = np.asarray(small, dtype=np.int16)
    bits = (arr[:, 1:] > arr[:, :-1]).ravel()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def _blur_score(gray: Image.Image) -> float:
    img = gray.resize((256, 256), Image.Resampling.BILINEAR)
    arr = np.asarray(img, dtype=np.float32)
    return float(ndimage.laplace(arr).var())


def inspect_image(args):
    root, rel = args
    path = Path(root) / rel
    try:
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        with Image.open(io.BytesIO(data)) as im:
            fmt = im.format or ""
            width, height = im.size
            im = ImageOps.exif_transpose(im)
            gray = im.convert("L")
            dhash = _dhash(gray)
            blur = _blur_score(gray)
        return {
            "path": rel,
            "ok": True,
            "sha256": sha,
            "dhash": dhash,
            "blur": blur,
            "width": width,
            "height": height,
            "bytes": len(data),
            "format": fmt,
            "error": "",
        }
    except Exception as exc:  # 损坏 / 无法解码
        return {
            "path": rel,
            "ok": False,
            "sha256": "",
            "dhash": 0,
            "blur": 0.0,
            "width": 0,
            "height": 0,
            "bytes": path.stat().st_size if path.exists() else 0,
            "format": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def load_splits(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    root = Path(data["root"])
    mapping = {}
    for split in ("train", "val", "test"):
        for rel, _label in data[split]:
            mapping[rel.replace("\\", "/")] = split
    return root, data, mapping


def list_files(root: Path):
    files = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = Path(dirpath) / name
            files.append(str(full.relative_to(root)).replace("\\", "/"))
    return sorted(files)


def _signature(root: Path, rel: str):
    with Image.open(root / rel) as im:
        gray = im.convert("L").resize((64, 64), Image.Resampling.BILINEAR)
        arr = np.asarray(gray, dtype=np.float32).ravel()
        arr = arr - arr.mean()
        std = arr.std()
        return arr / std if std > 1e-6 else arr


def _ncc(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / len(a))


def _candidate_pairs(results):
    buckets = [defaultdict(list) for _ in range(NEAR_BANDS)]
    for i, r in enumerate(results):
        if not r["ok"]:
            continue
        h = r["dhash"]
        for band in range(NEAR_BANDS):
            buckets[band][(h >> (band * BAND_BITS)) & 0xFFFF].append(i)

    pairs = {}
    skipped = 0
    for band in range(NEAR_BANDS):
        for ids in buckets[band].values():
            if len(ids) < 2:
                continue
            if len(ids) > BUCKET_CAP:
                skipped += 1
                continue
            for a in range(len(ids)):
                ia = ids[a]
                ha = results[ia]["dhash"]
                for b in range(a + 1, len(ids)):
                    ib = ids[b]
                    dist = (ha ^ results[ib]["dhash"]).bit_count()
                    if dist <= DHASH_MAX:
                        key = (ia, ib) if ia < ib else (ib, ia)
                        if key not in pairs or dist < pairs[key]:
                            pairs[key] = dist
    return pairs, skipped


def build_groups(results, mapping, root: Path, ncc_threshold: float):
    parent = list(range(len(results)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    exact = defaultdict(list)
    for i, r in enumerate(results):
        if r["ok"]:
            exact[r["sha256"]].append(i)
    for ids in exact.values():
        for i in ids[1:]:
            union(ids[0], i)

    candidates, skipped = _candidate_pairs(results)
    sig_cache = {}
    verified = {}
    ncc_values = []

    def get_sig(i):
        if i not in sig_cache:
            sig_cache[i] = _signature(root, results[i]["path"])
        return sig_cache[i]

    for (ia, ib), dist in candidates.items():
        ncc = _ncc(get_sig(ia), get_sig(ib))
        ncc_values.append(ncc)
        if ncc >= ncc_threshold:
            verified[(ia, ib)] = (dist, ncc)
            union(ia, ib)

    groups = defaultdict(list)
    for i, _r in enumerate(results):
        if results[i]["ok"]:
            groups[find(i)].append(i)

    exact_root = {}
    for sha, ids in exact.items():
        if len(ids) > 1:
            exact_root[find(ids[0])] = sha

    group_rows = []
    for root_id, ids in groups.items():
        if len(ids) < 2:
            continue
        paths = [results[i]["path"] for i in ids]
        classes = sorted({p.split("/")[0] for p in paths})
        splits = sorted({mapping.get(p, "unknown") for p in paths})
        nccs = [
            verified[(a, b)][1]
            for a in ids
            for b in ids
            if a < b and (a, b) in verified
        ]
        dists = [
            verified[(a, b)][0]
            for a in ids
            for b in ids
            if a < b and (a, b) in verified
        ]
        group_rows.append(
            {
                "group_id": len(group_rows) + 1,
                "kind": "exact" if root_id in exact_root else "near",
                "sha256": exact_root.get(root_id, ""),
                "size": len(ids),
                "min_distance": min(dists) if dists else 0,
                "ncc_max": max(nccs) if nccs else 1.0,
                "classes": classes,
                "splits": splits,
                "cross_class": len(classes) > 1,
                "cross_split": len(splits) > 1,
                "paths": paths,
            }
        )

    group_rows.sort(key=lambda r: (-r["size"], r["group_id"]))
    for i, row in enumerate(group_rows, 1):
        row["group_id"] = i

    direct = []
    for (ia, ib), (dist, ncc) in verified.items():
        direct.append(
            {
                "path_a": results[ia]["path"],
                "class_a": results[ia]["path"].split("/")[0],
                "split_a": mapping.get(results[ia]["path"], "unknown"),
                "path_b": results[ib]["path"],
                "class_b": results[ib]["path"].split("/")[0],
                "split_b": mapping.get(results[ib]["path"], "unknown"),
                "dhash_distance": dist,
                "ncc": round(ncc, 6),
            }
        )
    direct.sort(key=lambda r: (-r["ncc"], r["dhash_distance"]))

    return {
        "groups": group_rows,
        "direct_pairs": direct,
        "candidate_pairs": len(candidates),
        "verified_pairs": len(verified),
        "skipped_buckets": skipped,
        "ncc_values": ncc_values,
    }


def write_group_csv(path: Path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "group_id",
                "kind",
                "sha256",
                "size",
                "min_distance",
                "ncc_max",
                "classes",
                "splits",
                "cross_class",
                "cross_split",
                "paths",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r["group_id"],
                    r["kind"],
                    r["sha256"],
                    r["size"],
                    r["min_distance"],
                    f"{r['ncc_max']:.6f}",
                    ";".join(r["classes"]),
                    ";".join(r["splits"]),
                    "yes" if r["cross_class"] else "no",
                    "yes" if r["cross_split"] else "no",
                    " | ".join(r["paths"]),
                ]
            )


def write_simple_csv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="PlantVillage 数据集质量审计")
    parser.add_argument("--splits", type=Path, default=DEFAULT_SPLITS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    parser.add_argument("--limit", type=int, default=0, help="仅审计前 N 张（0=全部）")
    parser.add_argument("--blur-threshold", type=float, default=30.0, help="确认模糊阈值")
    parser.add_argument("--review-threshold", type=float, default=50.0, help="待复核阈值")
    parser.add_argument("--ncc-threshold", type=float, default=0.95, help="近同图 NCC 阈值")
    args = parser.parse_args()

    root, split_data, mapping = load_splits(args.splits)
    files = list_files(root)
    total_disk = len(files)
    if args.limit:
        files = files[: args.limit]

    print(f"数据集: {root}")
    print(f"磁盘文件: {total_disk}，本次审计: {len(files)}，进程: {args.workers}")
    args.out.mkdir(parents=True, exist_ok=True)

    started = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(inspect_image, (str(root), rel)) for rel in files]
        for done, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if done % 2000 == 0 or done == len(files):
                print(f"  已处理 {done}/{len(files)}，{time.time() - started:.1f}s")

    results.sort(key=lambda r: r["path"])
    valid = [r for r in results if r["ok"]]
    corrupt = [r for r in results if not r["ok"]]

    format_counts = Counter(r["format"] for r in valid)
    dims = Counter(f"{r['width']}x{r['height']}" for r in valid)
    blur_values = np.array([r["blur"] for r in valid], dtype=np.float64)
    blur_stats = {
        "min": float(blur_values.min()) if len(blur_values) else 0,
        "p1": float(np.percentile(blur_values, 1)) if len(blur_values) else 0,
        "p5": float(np.percentile(blur_values, 5)) if len(blur_values) else 0,
        "median": float(np.median(blur_values)) if len(blur_values) else 0,
        "p95": float(np.percentile(blur_values, 95)) if len(blur_values) else 0,
        "max": float(blur_values.max()) if len(blur_values) else 0,
    }
    blurred = []
    for r in valid:
        if r["blur"] < args.blur_threshold:
            severity = "confirmed"
        elif r["blur"] < args.review_threshold:
            severity = "review"
        else:
            continue
        blurred.append(
            {
                "path": r["path"],
                "class": r["path"].split("/")[0],
                "split": mapping.get(r["path"], "unknown"),
                "blur_variance": f"{r['blur']:.2f}",
                "severity": severity,
                "width": r["width"],
                "height": r["height"],
                "bytes": r["bytes"],
            }
        )
    blurred.sort(key=lambda r: float(r["blur_variance"]))

    dup = build_groups(results, mapping, root, args.ncc_threshold)
    groups = dup["groups"]
    exact_groups = [g for g in groups if g["kind"] == "exact"]
    near_groups = [g for g in groups if g["kind"] == "near"]
    cross_class = [g for g in groups if g["cross_class"]]
    cross_split = [g for g in groups if g["cross_split"]]
    direct = dup["direct_pairs"]

    direct_cross_class = [
        p for p in direct if p["class_a"] != p["class_b"]
    ]
    direct_cross_split = [
        p for p in direct if p["split_a"] != p["split_b"]
    ]
    direct_test_train = [
        p
        for p in direct
        if {p["split_a"], p["split_b"]} == {"test", "train"}
    ]

    test_leak_paths = set()
    val_leak_paths = set()
    for g in cross_split:
        splits = set(g["splits"])
        if "test" in splits and "train" in splits:
            test_leak_paths.update(p for p in g["paths"] if mapping.get(p) == "test")
        if "val" in splits and "train" in splits:
            val_leak_paths.update(p for p in g["paths"] if mapping.get(p) == "val")

    class_counts = Counter(r["path"].split("/")[0] for r in valid)
    split_counts = Counter(mapping.get(r["path"], "unknown") for r in valid)
    ncc_values = np.array(dup["ncc_values"], dtype=np.float64)

    summary = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "root": str(root),
        "splits_file": str(args.splits),
        "total_on_disk": total_disk,
        "audited": len(files),
        "readable": len(valid),
        "corrupt": len(corrupt),
        "formats": dict(format_counts),
        "dimensions_top": dict(dims.most_common(10)),
        "not_256_square": sum(c for d, c in dims.items() if d != "256x256"),
        "split_counts": dict(split_counts),
        "class_counts": dict(sorted(class_counts.items())),
        "blur": blur_stats,
        "blur_threshold": args.blur_threshold,
        "blur_review_threshold": args.review_threshold,
        "blur_confirmed": sum(1 for r in valid if r["blur"] < args.blur_threshold),
        "blur_review": sum(
            1 for r in valid if args.blur_threshold <= r["blur"] < args.review_threshold
        ),
        "blur_lt_100": sum(1 for r in valid if r["blur"] < 100),
        "candidate_pairs": dup["candidate_pairs"],
        "skipped_buckets": dup["skipped_buckets"],
        "ncc_threshold": args.ncc_threshold,
        "ncc_p95": float(np.percentile(ncc_values, 95)) if len(ncc_values) else 0,
        "verified_pairs": dup["verified_pairs"],
        "direct_cross_class_pairs": len(direct_cross_class),
        "direct_cross_split_pairs": len(direct_cross_split),
        "direct_test_train_pairs": len(direct_test_train),
        "duplicate_groups": len(groups),
        "exact_groups": len(exact_groups),
        "exact_images": sum(g["size"] for g in exact_groups),
        "near_groups": len(near_groups),
        "near_images": sum(g["size"] for g in near_groups),
        "cross_class_groups": len(cross_class),
        "cross_split_groups": len(cross_split),
        "leaked_test_images": len(test_leak_paths),
        "leaked_val_images": len(val_leak_paths),
        "elapsed_seconds": round(time.time() - started, 1),
    }

    write_simple_csv(
        args.out / "image_index.csv",
        [
            "path",
            "class",
            "split",
            "ok",
            "sha256",
            "dhash",
            "blur_variance",
            "width",
            "height",
            "bytes",
            "format",
            "error",
        ],
        [
            {
                "path": r["path"],
                "class": r["path"].split("/")[0],
                "split": mapping.get(r["path"], "unknown"),
                "ok": "yes" if r["ok"] else "no",
                "sha256": r["sha256"],
                "dhash": f"{r['dhash']:016x}",
                "blur_variance": f"{r['blur']:.2f}",
                "width": r["width"],
                "height": r["height"],
                "bytes": r["bytes"],
                "format": r["format"],
                "error": r["error"],
            }
            for r in results
        ],
    )
    write_group_csv(args.out / "duplicates.csv", groups)
    write_group_csv(args.out / "duplicates_exact.csv", exact_groups)
    write_group_csv(args.out / "duplicates_cross_class.csv", cross_class)
    write_group_csv(args.out / "duplicates_cross_split.csv", cross_split)
    write_simple_csv(
        args.out / "leakage_pairs.csv",
        [
            "split_a",
            "split_b",
            "class_a",
            "class_b",
            "dhash_distance",
            "ncc",
            "path_a",
            "path_b",
        ],
        direct_cross_split,
    )
    write_simple_csv(
        args.out / "blurred.csv",
        [
            "path",
            "class",
            "split",
            "blur_variance",
            "severity",
            "width",
            "height",
            "bytes",
        ],
        blurred,
    )
    write_simple_csv(
        args.out / "corrupt.csv",
        ["path", "error", "bytes"],
        [{"path": r["path"], "error": r["error"], "bytes": r["bytes"]} for r in corrupt],
    )
    (args.out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n审计完成")
    print(f"  可读 {len(valid)} / 损坏 {len(corrupt)}")
    print(f"  精确重复组 {len(exact_groups)}（{summary['exact_images']} 张）")
    print(
        f"  近同图 {len(near_groups)} 组（{summary['near_images']} 张，NCC>={args.ncc_threshold}）"
    )
    print(
        f"  直接跨类对 {len(direct_cross_class)}，跨划分对 {len(direct_cross_split)}，test-train {len(direct_test_train)}"
    )
    print(f"  跨类组 {len(cross_class)}，跨划分组 {len(cross_split)}")
    print(f"  疑似泄漏：test {len(test_leak_paths)} 张，val {len(val_leak_paths)} 张")
    print(
        f"  模糊：确认 {summary['blur_confirmed']} 张（<{args.blur_threshold}），"
        f"待复核 {summary['blur_review']} 张（{args.blur_threshold}~{args.review_threshold}）"
    )
    print(f"  输出目录 {args.out}")


if __name__ == "__main__":
    main()

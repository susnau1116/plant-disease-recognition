"""根据数据审计结果生成隔离清单与“清洗版”划分（不修改原图与原划分）。

- 重复组保留一张（优先 train、非确认模糊、清晰度最高），其余进入隔离清单；
- 确认模糊（blur_variance < 阈值）进入隔离清单；
- 待复核模糊只标记，不隔离；
- 输出：
  model/logs/data_audit/quarantine.csv
  model/logs/data_audit/cleaning_summary.json
  model/data/splits/plantvillage_r70_15_15_seed42_cleaned.json
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
AUDIT_DIR = BASE_DIR / "logs" / "data_audit"
SPLITS = BASE_DIR / "data" / "splits" / "plantvillage_r70_15_15_seed42.json"
CLEAN_SPLITS = BASE_DIR / "data" / "splits" / "plantvillage_r70_15_15_seed42_cleaned.json"


def read_csv(name):
    with (AUDIT_DIR / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    index = {r["path"]: r for r in read_csv("image_index.csv")}
    groups = read_csv("duplicates.csv")
    blurred = read_csv("blurred.csv")

    confirmed_blur = {
        r["path"] for r in blurred if r["severity"] == "confirmed"
    }
    review_blur = {r["path"] for r in blurred if r["severity"] == "review"}

    quarantine = {}
    kept_for = {}
    for g in groups:
        paths = g["paths"].split(" | ")
        candidates = [p for p in paths if p in index]

        def score(p):
            info = index[p]
            return (
                info["split"] != "train",          # train 优先
                p in confirmed_blur,               # 非确认模糊优先
                -float(info["blur_variance"]),     # 越清晰越优先
            )

        candidates.sort(key=score)
        keep = candidates[0]
        kept_for[int(g["group_id"])] = keep
        for p in candidates[1:]:
            quarantine[p] = {
                "reason": "duplicate",
                "group_id": g["group_id"],
                "kept_path": keep,
            }

    for p in confirmed_blur:
        if p not in quarantine:
            quarantine[p] = {
                "reason": "blur",
                "group_id": "",
                "kept_path": "",
            }
        elif quarantine[p]["reason"] == "duplicate":
            quarantine[p]["reason"] = "duplicate+blur"

    original = json.loads(SPLITS.read_text(encoding="utf-8"))
    clean = {k: original[k] for k in ("root", "ratios", "seed", "classes")}
    clean["cleaned_from"] = SPLITS.name
    clean["excluded"] = sorted(quarantine)
    clean_counts = {}
    for split in ("train", "val", "test"):
        entries = [
            e
            for e in original[split]
            if e[0].replace("\\", "/") not in quarantine
        ]
        clean[split] = entries
        clean_counts[split] = len(entries)
    clean["counts"] = clean_counts
    clean["cleaning_note"] = (
        "excluded = 重复组保留一张后的其余图片 + 确认模糊图片；"
        "原划分文件 plantvillage_r70_15_15_seed42.json 保持不变。"
    )

    CLEAN_SPLITS.write_text(
        json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    fieldnames = [
        "path",
        "class",
        "split",
        "reason",
        "group_id",
        "kept_path",
        "blur_variance",
        "blur_severity",
    ]
    rows = []
    for p in sorted(quarantine):
        info = index[p]
        q = quarantine[p]
        rows.append(
            {
                "path": p,
                "class": info["class"],
                "split": info["split"],
                "reason": q["reason"],
                "group_id": q["group_id"],
                "kept_path": q["kept_path"],
                "blur_variance": info["blur_variance"],
                "blur_severity": "confirmed" if p in confirmed_blur else "",
            }
        )
    with (AUDIT_DIR / "quarantine.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    reason_counts = Counter(r["reason"] for r in rows)
    split_counts = Counter(r["split"] for r in rows)
    class_counts = Counter(r["class"] for r in rows)
    duplicate_extras = sum(1 for r in rows if "duplicate" in r["reason"])
    blur_only = sum(1 for r in rows if r["reason"] == "blur")
    both = sum(1 for r in rows if r["reason"] == "duplicate+blur")

    original_counts = {k: len(original[k]) for k in ("train", "val", "test")}
    summary = {
        "original_counts": original_counts,
        "cleaned_counts": clean_counts,
        "excluded_total": len(quarantine),
        "excluded_by_reason": dict(reason_counts),
        "excluded_by_split": dict(split_counts),
        "excluded_by_class": dict(sorted(class_counts.items(), key=lambda x: -x[1])),
        "duplicate_groups": len(groups),
        "duplicate_extras": duplicate_extras,
        "blur_confirmed": len(confirmed_blur),
        "blur_review_not_excluded": len(review_blur),
        "duplicate_and_blur": both,
        "quarantine_csv": str(AUDIT_DIR / "quarantine.csv"),
        "cleaned_splits": str(CLEAN_SPLITS),
        "note": "原图与原始划分未改动；清洗版划分仅用于后续实验。",
    }
    (AUDIT_DIR / "cleaning_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

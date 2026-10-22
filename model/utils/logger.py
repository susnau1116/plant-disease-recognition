"""日志与训练历史记录。"""

import csv
import logging
import time
from pathlib import Path


def setup_logger(log_file) -> logging.Logger:
    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("train")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return logger


def write_history_csv(path, history: list, fieldnames=None) -> None:
    """整体重写 history.csv，断点续训后历史同样完整。"""
    if not history:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = fieldnames or list(history[0].keys())
    for attempt in range(10):
        try:
            with path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in history:
                    writer.writerow({key: row.get(key, "") for key in fieldnames})
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(3)

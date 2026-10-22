"""专家咨询：FAQ 关键词匹配 + 文本相似度。

策略：
- 对问题做归一化（去标点/空白、转小写）
- 关键词命中得分（按关键词长度加权）
- 与 FAQ 问题文本计算字符二元组 Dice 相似度
- 综合得分 = 0.6 * 关键词得分 + 0.4 * 相似度；低于阈值视为未匹配
- 未匹配时给出引导语（建议上传图片识别或稍后留言）
"""

import json
import re
from functools import lru_cache

from .. import database as db

STOP_CHARS = re.compile(r"[\s，。？！、；：“”‘’（）《》【】,.?!;:\"'()\[\]<>~·\-—_/\\|]+")
THRESHOLD = 0.25


def normalize(text: str) -> str:
    return STOP_CHARS.sub("", text.lower())


def bigrams(text: str):
    return {text[i : i + 2] for i in range(len(text) - 1)} if len(text) > 1 else {text}


def dice(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return dice_sets(bigrams(a), bigrams(b))


def dice_sets(sa, sb) -> float:
    if not sa or not sb:
        return 0.0
    return 2 * len(sa & sb) / (len(sa) + len(sb))


def _keyword_score(question_norm: str, keywords):
    if not keywords:
        return 0.0
    hit_weight = 0.0
    total_weight = 0.0
    for kw in keywords:
        k = normalize(kw)
        if not k:
            continue
        weight = min(len(k), 6)
        total_weight += weight
        if k in question_norm:
            hit_weight += weight
    if total_weight == 0:
        return 0.0
    return min(hit_weight / total_weight * 1.5, 1.0)


@lru_cache(maxsize=1)
def _faq_index():
    """预计算 FAQ 的归一化文本与字符二元组，避免每次咨询重复处理。"""
    rows = db.query("SELECT * FROM faqs ORDER BY id")
    index = []
    for r in rows:
        q_norm = normalize(r["question"])
        index.append(
            (
                _faq(r),
                json.loads(r["keywords"] or "[]"),
                q_norm,
                bigrams(q_norm),
                normalize(r["answer"]),
            )
        )
    return tuple(index)


def consult(question: str, related_limit: int = 3):
    """返回 (matched, score, best_faq | None, related_faqs, suggestion)。"""
    question_norm = normalize(question)
    question_bigrams = bigrams(question_norm)
    scored = []
    for faq, keywords, q_norm, q_bigrams, a_norm in _faq_index():
        k_score = _keyword_score(question_norm, keywords)
        sim = dice_sets(question_bigrams, q_bigrams)
        if question_norm and question_norm in a_norm:
            sim = max(sim, 0.6)
        score = round(0.6 * k_score + 0.4 * sim, 4)
        scored.append((score, faq))

    scored.sort(key=lambda x: -x[0])
    best_score, best_faq = scored[0] if scored else (0.0, None)
    related = [faq for s, faq in scored[1 : 1 + related_limit] if s > 0.1]

    if best_faq is not None and best_score >= THRESHOLD:
        return True, best_score, best_faq, related, ""

    suggestion = (
        "抱歉，知识库中暂未找到与您问题直接匹配的答案。"
        "您可以：① 换个说法再试一次；② 在首页上传叶片照片进行病害识别，识别后可查看对应防治方案；"
        "③ 点击「留言提问」提交问题，工作人员会尽快回复。"
    )
    return False, best_score, None, related, suggestion


def _faq(row):
    return {
        "id": row["id"],
        "category": row["category"],
        "question": row["question"],
        "answer": row["answer"],
        "keywords": json.loads(row["keywords"] or "[]"),
    }


def clear_cache():
    _faq_index.cache_clear()

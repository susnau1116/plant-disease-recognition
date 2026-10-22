"""专家咨询接口：FAQ 列表与智能问答。"""

from typing import Optional

from fastapi import APIRouter, Query

from .. import schemas
from ..services import consult as consult_service
from ..services import knowledge

router = APIRouter(tags=["专家咨询"])


@router.get("/faqs", response_model=schemas.FaqListResponse, summary="FAQ 列表")
def faqs(category: Optional[str] = Query(None, description="按分类筛选")):
    items = knowledge.list_faqs(category)
    return {
        "categories": knowledge.get_categories(),
        "total": len(items),
        "items": items,
    }


@router.post("/consult", response_model=schemas.ConsultResponse, summary="专家咨询问答")
def consult(payload: schemas.ConsultRequest):
    matched, score, answer, related, suggestion = consult_service.consult(payload.question)
    return {
        "matched": matched,
        "score": score,
        "answer": answer,
        "related": related,
        "suggestion": suggestion,
    }

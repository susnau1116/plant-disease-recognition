"""病害知识库接口：作物列表、病害检索与详情（含防治方案与防治效果）。"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from .. import schemas
from ..services import knowledge

router = APIRouter(tags=["知识库"])


@router.get("/crops", response_model=List[schemas.CropItem], summary="作物列表")
def crops():
    return knowledge.list_crops()


@router.get("/diseases", response_model=schemas.DiseaseListResponse, summary="病害列表/检索")
def diseases(
    crop: Optional[str] = Query(None, description="按作物筛选"),
    q: Optional[str] = Query(None, description="关键词：中文名/英文名/类别名/症状"),
    healthy: Optional[bool] = Query(None, description="true 只看健康，false 只看病害"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total, items = knowledge.list_diseases(crop=crop, q=q, healthy=healthy, page=page, page_size=page_size)
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/diseases/{class_name}", response_model=schemas.DiseaseDetail, summary="病害详情")
def disease_detail(class_name: str, request: Request):
    disease = knowledge.get_disease(class_name, base_url=str(request.base_url))
    if disease is None:
        raise HTTPException(status_code=404, detail=f"未找到类别: {class_name}")
    return disease

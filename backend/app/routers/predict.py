"""图像识别接口：上传叶片图片 → 返回病害类别、置信度与防治方案。"""

import asyncio
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from .. import config, schemas
from ..services import knowledge
from ..services.predictor import InvalidImageError, predictor

router = APIRouter(tags=["识别"])
_inference_slots = asyncio.Semaphore(config.MAX_CONCURRENT_INFERENCE)


@router.post("/predict", response_model=schemas.PredictResponse, summary="叶片病害识别")
async def predict(
    request: Request,
    file: UploadFile = File(..., description="叶片图片（jpg / png / bmp / webp）"),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix and suffix not in config.ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式: {suffix}")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="上传文件为空")
    if len(content) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="图片超过 10 MB 限制")

    try:
        async with _inference_slots:
            topk, elapsed_ms = await run_in_threadpool(
                predictor.predict, content, config.TOP_K
            )
    except InvalidImageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    classes = predictor.classes

    top_items = []
    for idx, prob in topk:
        class_name = classes[idx]
        brief = knowledge.get_briefs([class_name]).get(class_name)
        if not brief:
            continue
        top_items.append(
            {
                "class_name": class_name,
                "name_cn": brief["name_cn"],
                "crop": brief["crop"],
                "confidence": round(prob, 4),
            }
        )

    top_class = classes[topk[0][0]]
    disease = knowledge.get_disease(top_class, base_url=str(request.base_url))
    if disease is None:
        raise HTTPException(status_code=500, detail=f"知识库缺少类别 {top_class} 的信息")

    return {
        "class_name": top_class,
        "name_cn": disease["name_cn"],
        "crop": disease["crop"],
        "healthy": disease["healthy"],
        "confidence": round(topk[0][1], 4),
        "top_k": top_items,
        "disease": disease,
        "inference_ms": round(elapsed_ms, 1),
    }

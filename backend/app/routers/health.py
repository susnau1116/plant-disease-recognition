"""健康检查与系统信息。"""

from fastapi import APIRouter

from .. import __version__, schemas
from ..services import knowledge
from ..services.predictor import predictor

router = APIRouter(tags=["系统"])


@router.get("/health", response_model=schemas.HealthResponse, summary="健康检查")
def health():
    predictor.load()
    stats = knowledge.stats()
    return {
        "status": "ok",
        "model": predictor.model_name,
        "classes": len(predictor.classes),
        "diseases": stats["diseases"],
        "faqs": stats["faqs"],
        "version": __version__,
    }

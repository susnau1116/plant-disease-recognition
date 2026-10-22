"""FastAPI 应用入口。

启动：
    cd backend
    uvicorn app.main:app --host 0.0.0.0 --port 8000
文档：
    http://127.0.0.1:8000/docs
"""

import hashlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__, config
from .routers import consult, diseases, health, messages, predict
from .services import consult as consult_service
from .services import knowledge
from .services.predictor import predictor

DESCRIPTION = """
基于深度学习的农作物病害识别与防治系统后端服务：

- **识别**：上传叶片图片，返回病害类别、置信度与 Top-K 结果（ResNet18 + ONNX Runtime）
- **防治推荐**：按识别结果匹配农药 / 物理 / 农业防治方案，含预期效果、见效时间与效果判断标准
- **知识库**：38 类病害的症状、发病规律、传播途径与防治方案查询
- **专家咨询**：FAQ 关键词匹配问答，未匹配时可留言，工作人员回复后用户端可见
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .database import init_db

    init_db()
    if knowledge.stats()["diseases"] == 0:
        from scripts.import_knowledge import import_all
        from .database import connect

        with connect() as conn:
            import_all(conn, verbose=False)
    knowledge.clear_cache()
    consult_service.clear_cache()
    predictor.load()  # 预判模型
    yield


app = FastAPI(
    title="农作物病害识别与防治系统 API",
    description=DESCRIPTION,
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)


def _is_knowledge_get(path: str) -> bool:
    return path in ("/api/crops", "/api/faqs", "/api/diseases") or path.startswith(
        "/api/diseases/"
    )


def _knowledge_etag(request: Request) -> str:
    """按完整 URL（含查询参数）生成 ETag，避免不同筛选条件共用缓存。"""
    raw = f"{config.KNOWLEDGE_ETAG}|{request.url.path}|{request.url.query}"
    return 'W/"' + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20] + '"'


@app.middleware("http")
async def cache_headers(request: Request, call_next):
    """静态例图与只读知识库接口加缓存头；知识库 ETag 命中时直接 304。"""
    path = request.url.path
    if request.method == "GET" and _is_knowledge_get(path):
        etag = _knowledge_etag(request)
        headers = {
            "ETag": etag,
            "Cache-Control": f"public, max-age={config.CACHE_MAX_AGE_KNOWLEDGE}",
            "Access-Control-Allow-Origin": "*",
        }
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        response = await call_next(request)
        for key, value in headers.items():
            response.headers.setdefault(key, value)
        return response
    if request.method == "GET" and path.startswith("/static/"):
        response = await call_next(request)
        response.headers.setdefault(
            "Cache-Control", f"public, max-age={config.CACHE_MAX_AGE_STATIC}"
        )
        return response
    return await call_next(request)

app.include_router(health.router, prefix="/api")
app.include_router(predict.router, prefix="/api")
app.include_router(diseases.router, prefix="/api")
app.include_router(consult.router, prefix="/api")
app.include_router(messages.router, prefix="/api")

# 例图等静态资源：/static/examples/<class_name>/<n>.jpg
config.STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def root():
    return {
        "name": "农作物病害识别与防治系统 API",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/health",
    }

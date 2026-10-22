# 后端服务（FastAPI）

基于 FastAPI 的农作物病害识别与防治系统后端，提供图像识别、病害知识库与专家咨询接口。

## 功能

- **图像识别** `/api/predict`：上传叶片图片 → ResNet18（ONNX Runtime）推理 → 返回类别、置信度与 Top-K
- **防治推荐** `/api/diseases`、`/api/diseases/{class_name}`：38 类病害详情 + 农药/物理/农业防治方案（含预期效果、见效时间、判断标准、未达预期处理）
- **专家咨询** `/api/consult`、`/api/faqs`：FAQ 关键词匹配问答，未匹配时返回留言引导
- **留言** `/api/messages`、`/api/messages/{id}`、`/api/messages/{id}/reply`：未匹配问题提交、列表/详情查询与回复
- **健康检查** `/api/health`

## 快速开始

```bash
cd backend
pip install -r requirements.txt

# 导入知识库（JSON → SQLite；修改 data/ 下 JSON 后需重新执行）
python scripts/import_knowledge.py

# 启动服务（首次启动若数据库为空会自动导入）
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Swagger 文档：http://127.0.0.1:8000/docs
- 接口前缀统一为 `/api`，已开启 CORS（允许移动端 / Web 跨域调用）

## 配置（环境变量）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `CROP_MODEL` | （空，FP32） | 设为 `quantized` 使用量化模型 `models/resnet18_quantized.onnx` |
| `CROP_DB_PATH` | `backend/database/app.db` | SQLite 路径 |
| `CROP_ORT_THREADS` | `min(8, CPU 逻辑核数)` | ONNX Runtime 推理线程数；本机 12 线程实测 8 线程优于全核 |
| `CROP_MAX_CONCURRENT_INFERENCE` | `2` | 同时执行的识别任务上限（信号量） |
| `CROP_JPEG_DRAFT_MIN_SIZE` | `1024` | 最短边大于该值的 JPEG 在解码阶段 draft 降采样；设为 `0` 关闭 |

## 目录结构

```
backend/
├── app/
│   ├── main.py            # FastAPI 入口（lifespan 自动初始化、CORS）
│   ├── config.py          # 路径与预处理常量
│   ├── database.py        # SQLite 连接与建表
│   ├── schemas.py         # Pydantic 模型
│   ├── routers/           # health / predict / diseases / consult / messages
│   └── services/          # predictor(ONNX) / knowledge / consult
├── scripts/import_knowledge.py   # JSON → SQLite 导入（启动时自动兜底）
├── data/                  # 病害知识库 JSON（14 作物） + faq.json
├── models/                # resnet18.onnx / resnet18_quantized.onnx / classes.txt
├── database/app.db        # 生成的 SQLite（含 messages 留言表）
└── tests/                 # pytest（23 项，含真实图片端到端识别与留言）
```

## 测试

```bash
cd backend
python -m pytest          # 23 项：识别 / 知识库 / 咨询 / 留言 / 健康检查
```

## 重要提醒

1. **预处理一致性（关键）**：`services/predictor.py` 的预处理必须与训练/评估一致 —— PIL 读图 → RGB → 短边 Resize 256 → CenterCrop 224 → /255 → ImageNet 归一化；类别顺序取自 `models/classes.txt`（= 训练时的 `classes` 顺序），迁移其他模型时两样都要同步替换。
2. **知识库数据源**：只改 `data/diseases/*.json` 与 `data/faq.json`，改完必须 `python scripts/import_knowledge.py` 重新导入（或删除 `database/app.db` 后重启）。知识库查询已做进程内缓存，重新导入后需重启服务缓存才会刷新。
3. **模型文件**：`models/` 下的 ONNX 与 classes.txt 是从 `model/onnx_models/` 拷贝的产物；重新训练/导出后需再次拷贝。
4. **本机无 GPU**：动态量化模型在本机 CPU 上反而略慢（体积收益为主），默认加载 FP32；切换用 `CROP_MODEL=quantized`。
5. 中文路径下 onnxruntime 读取模型文件无问题，但不要用非 Python 文件对象手工处理 ONNX 字节流。
6. **性能优化（2026-10-20）**：识别只解码一次图片；大图 JPEG 用 draft 降采样（最终仍 Resize(256) → CenterCrop(224)）；模型启动时 warm-up；`/predict` 在线程池执行并用信号量限流；知识库/FAQ/consult 结果进程内缓存；响应启用 GZip 与 Cache-Control/ETag。实测单张识别 22~24 ms → 15~16 ms，作物/详情/FAQ 接口 4~6 ms → 约 3 ms（病害列表因动态筛选约 5 ms）。修改这些参数后重启服务生效。

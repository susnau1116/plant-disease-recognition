# Web 端（Vue3 + Vite）

农作物病害识别与防治系统 Web 前端，提供图片上传识别、识别结果与防治方案展示、病害知识库、专家咨询、留言提交与回复管理五个功能模块。

## 快速开始

```bash
cd web
npm install --registry=https://registry.npmmirror.com   # 国内镜像，秒装
npm run dev        # http://127.0.0.1:5173（/api 代理到 127.0.0.1:8000）
```

**先启动后端**（`backend` 目录：`uvicorn app.main:app --port 8000`），否则页面能打开但接口报错。

生产构建：

```bash
npm run build      # 输出 dist/
npm run preview    # 本地预览构建产物
```

## 页面结构

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/` | HomeView | 首页：上传/拖拽图片识别，系统概况 |
| `/result` | ResultView | 识别结果：置信度、Top-K、病害信息、防治方案 |
| `/knowledge` | KnowledgeView | 知识库：作物筛选 + 关键词检索 + 分页 |
| `/knowledge/:className` | DiseaseDetailView | 病害详情与防治效果 |
| `/consult` | ConsultView | 专家咨询：分类常见问题 + 对话式问答 + 未匹配留言 |
| `/messages` | MessagesView | 留言管理：状态筛选、查看与回复留言 |

## 后端地址配置

- 开发环境：`vite.config.js` 的 `server.proxy` 将 `/api` 转发到 `http://127.0.0.1:8000`
- 生产环境：构建时用环境变量指定后端地址，如 `VITE_API_BASE=http://服务器IP:8000/api npm run build`；或部署后用 Nginx 反代 `/api`

## 重要提醒

1. **先起后端再联调**：识别接口依赖后端 ONNX 模型，后端未启动时首页统计会显示默认值、识别报错。
2. **上传限制**：前端限制 10 MB、图片格式（JPG/PNG/BMP/WEBP），与后端 `MAX_UPLOAD_BYTES` 保持一致。
3. **识别结果页依赖内存状态**：结果通过 `src/store.js` 传递，刷新 `/result` 会回到空状态，属预期行为。
4. **样式约定**：无 UI 组件库，主题变量集中在 `src/assets/styles.css`（绿色农业主题），改主题优先改变量。

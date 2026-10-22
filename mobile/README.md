# 移动端 App（uni-app）

农作物病害识别与防治系统移动端，支持拍照/相册上传识别、防治方案查看、病害知识库与专家咨询。一套代码可发布为 H5 / Android / iOS / 微信小程序。

## 运行方式

### 方式一：浏览器 H5 预览（CLI，无需 HBuilderX）

```bash
cd mobile
npm install --registry=https://registry.npmmirror.com
npm run dev:h5        # http://127.0.0.1:5174
npm run build:h5      # 构建 H5 产物
```

> 工程为 HBuilderX 目录结构（app 文件在根目录），CLI 通过 `UNI_INPUT_DIR=.` 指定输入目录（见 package.json / vite.config.js）。

### 方式二：HBuilderX（App / 小程序 / 真机）

1. 用 HBuilderX 打开 `mobile/` 目录（Vue3 工程，manifest.json 已设 `vueVersion: "3"`）
2. 运行 → 运行到浏览器（H5）/ 运行到手机或模拟器（App）/ 运行到小程序模拟器
3. 打包：发行 → 原生 App 云打包（Android/iOS）或小程序上传

## 后端地址配置（重要）

`api/index.js` 顶部的 `BASE_URL` 当前为 `http://192.168.1.125:8000/api`（电脑局域网 IP，2026-10-16 打包 APK 前修改；H5 本机调试可改回 `http://127.0.0.1:8000/api`）：

| 调试方式 | BASE_URL |
| --- | --- |
| 浏览器 H5（电脑本机 5174） | `http://127.0.0.1:8000/api`（或局域网 IP 亦可） |
| 手机浏览器访问电脑的 5174 | 电脑局域网 IP，如 `http://192.168.1.100:8000/api`（手机与电脑需同一 WiFi） |
| App 真机 / 模拟器 | 同上，改为电脑局域网 IP（打包后固定，换网络需重改并**重新打包**） |
| 发布 | 改为服务器地址 |

后端已开启 CORS，无需额外配置；但**真机调试时必须先启动后端并且 IP 可达**。

## 页面结构

| 页面 | 路径 | 说明 |
| --- | --- | --- |
| 识别首页 | `pages/index/index` | 拍照/相册上传，开始识别 |
| 识别结果 | `pages/result/result` | 置信度、Top-K、病害信息、防治方案（含防治效果） |
| 知识库 | `pages/knowledge/knowledge` | 作物筛选、关键词搜索、加载更多 |
| 病害详情 | `pages/knowledge/detail` | 按类别查看症状与防治方案 |
| 专家咨询 | `pages/consult/consult` | 常见问题 + 对话问答 + 未匹配留言入口 |
| 我的留言 | `pages/message/message` | 提交留言、查看回复（本地记录留言 ID） |

底部 tabBar 三个入口：识别 / 知识库 / 咨询。图标位于 `static/`（已生成，可直接替换）。

## 重要提醒

1. **结果传递**：识别结果通过 `uni.setStorageSync('lastResult')` 传给结果页，属临时缓存，重新识别会覆盖。
2. **图片压缩**：`uni.chooseImage` 已使用 `sizeType: ['compressed']`，避免大图上传超限（后端上限 10 MB）。
3. **打包前检查**：`manifest.json` 的 appid 已填 `__UNI__XXXXXXXX`（DCloud 账号 your-email@example.com，已绑手机号）；当前源码与最新 APK 均为 1.0.7 / 107（2026-10-20 云打包并完成真机留言闭环复验）。重新打包前先确认 `api/index.js` 的 BASE_URL 正确。
4. **页面标签**：uni-app 页面必须使用 `view/text/image/scroll-view` 等内置标签，不要改成 `div/span/img`。
5. **方式二（HBuilderX，App / 小程序 / 真机 / 云打包）**：HBuilderX 5.26 已安装于 `<HBuilderX 安装路径>`（含 launcher / app-safe-pack / amazon-corretto 插件）；Android APK 已云打包（最新 v1.0.7 / 107，含留言栏整条点击、留言功能与知识库/断网提示修复）：`unpackage/release/apk/plant-disease-v1.0.7.apk`（14.3 MB，包名 `com.graduation.plantdisease`，**云端证书**——公共测试证书已停用）；v1.0.7 已完成留言提交/回复/刷新闭环真机验证。重新打包命令：`cli pack --project mobile --platform android --android.packagename com.graduation.plantdisease --android.androidpacktype 3`（需登录 DCloud 账号；注意每日云打包次数限制）。真机调试前必须先启动后端（`--host 0.0.0.0`）并放行防火墙 8000（规则 CropDiseaseBackend8000）。

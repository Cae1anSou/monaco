# Vue 沙箱 & 实时静态检查

FastAPI + Docker 为每位开发者动态启动独立沙箱，并通过 ESLint 提供 IDE 级实时反馈。

## 功能亮点

-   零配置原型：直接编写、预览 Vue 组件  
-   实时静态检查：统一代码风格，问题早发现  
-   环境完全隔离：每个沙箱独立容器，互不干扰  
-   一键清理：用完即删，绝不污染本机



## 项目结构

```
.
├── backend/                # FastAPI 后端
│   ├── app/
│   │   └── main.py         # 核心应用逻辑，包括 Docker 和 ESLint 集成
│   └── requirements.txt    # Python 依赖
├── frontend/               # Monaco 前端编辑器
│   └── index.html          # 单页应用
├── hello-vue/              # Vue.js 沙箱环境模板
│   ├── src/
│   │   ├── App.vue
│   │   └── main.js
│   ├── Dockerfile          # 用于构建沙箱镜像
│   ├── index.html
│   ├── package.json
│   └── vite.config.mjs
├── .gitignore
├── package-lock.json
└── README.md
```

## 快速上手

1. 环境要求  
   Python ≥3.8、Node ≥16、Docker（需运行中）

2. 启动后端  
   ```bash
   cd backend
   pip install -r requirements.txt   # 首次
   uvicorn app.main:app --reload --port 8000
   ```

3. 创建沙箱  
   ```bash
   curl -X POST http://127.0.0.1:8000/sandbox/start \
     -H 'Content-Type: application/json' \
     -d '{"name":"hello-vue","path":"hello-vue","external_port":5173}'
   ```
   记下 `container_id`。

4. 打开前端  
   在 `frontend/index.html` 中替换 `CONTAINER_ID`，然后直接在浏览器打开该文件。

5. 结束并清理  
   ```bash
   curl -X POST http://127.0.0.1:8000/sandbox/<container_id>/stop
   ```

## API

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| /sandbox/start | POST | 构建镜像并启动沙箱 |
| /lint | POST | 在容器内执行 ESLint |
| /sandbox/{id}/logs | GET | 最近 200 行容器日志 |
| /sandbox/{id}/stop | POST | 停止并删除容器 |

## 调试 & 贡献

- ESLint 规则：修改 `backend/app/main.py` 中的 `eslint_config`  
- 前端调试：`frontend/index.html` 内 “调试静态检查” 按钮  
- 新增依赖：在 `hello-vue/package.json` 添加依赖并重建镜像

## FAQ

**Q: “Container not found”**  
A: 检查 `CONTAINER_ID` 是否正确，容器是否仍在运行。

**Q: 如何访问 Vue 应用？**  
A: 容器 5173 端口已映射至本机 5173，浏览器访问 `http://localhost:5173`。
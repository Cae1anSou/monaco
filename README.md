# Vue.js 实时沙箱与静态检查工具



后端使用 FastAPI 构建，通过动态管理 Docker 容器为每个开发者提供隔离的、即用即弃的沙箱环境。

## 核心目标

-   **快速原型验证**：无需搭建完整的本地环境，即可快速编写和测试 Vue 组件。
-   **统一代码规范**：通过集成的、可配置的 ESLint 规则，确保团队成员遵循统一的代码风格。
-   **提升开发效率**：提供类似 IDE 的实时反馈，在编码阶段就发现并修复问题。
-   **环境隔离**：每个沙箱运行在独立的 Docker 容器中，互不干扰。

## 架构概览

系统由三部分组成：**FastAPI 后端**、**Docker 沙箱** 和 **Monaco 前端编辑器**。

```mermaid
flowchart TD
    subgraph 用户浏览器
        A[开发人员]
        B[Monaco 前端编辑器]
    end

    subgraph 后端服务
        C[FastAPI 后端]
    end

    subgraph Docker 环境
        D[Docker 容器 (Vue 沙箱)]
    end

    A -- 打开 index.html --> B
    B -- 发送 Lint 请求(代码+容器ID) --> C
    C -- 执行 docker exec --> D
    D -- 返回 ESLint 结果 --> C
    C -- 返回 JSON 结果 --> B
    B -- 在编辑器中高亮问题 --> A
    C -- 创建/停止 --> D
```

-   **FastAPI 后端** (`backend/`): 负责处理 API 请求，核心逻辑是调用 Docker API 来创建、停止和与容器交互。
-   **Docker 沙箱** (`hello-vue/`): 一个标准的 Vue.js + Vite 开发环境，包含 ESLint 和相关插件。后端会基于此目录构建镜像。
-   **Monaco 前端编辑器** (`frontend/`): 一个单页 HTML 应用，集成了 Monaco Editor（VS Code 的核心组件），提供了丰富的代码编辑和实时静态检查功能。

## 快速开始：核心工作流

请遵循以下步骤来启动并使用完整的沙箱环境。

### 1. 环境准备

确保您的机器已安装并运行：
-   Python (3.8+)
-   Node.js (16+) & npm
-   Docker Desktop (**必须处于运行状态**)

### 2. 启动后端服务

```bash
# 1. 进入后端目录并安装依赖 (仅首次需要)
cd backend
pip install -r requirements.txt

# 2. 启动 FastAPI 服务
uvicorn app.main:app --reload --port 8000
```
服务将在 `http://127.0.0.1:8000` 运行。

### 3. 启动一个沙箱容器

打开一个新的终端，使用 `curl` 或 API 测试工具向后端发送请求，以创建一个新的沙箱容器。

```bash
curl -X POST http://127.0.0.1:8000/sandbox/start \
-H "Content-Type: application/json" \
-d '{
  "name": "hello-vue",
  "path": "hello-vue",
  "external_port": 5173
}'
```

成功后，您将收到如下响应。请**复制 `container_id`**，下一步会用到。
```json
{
  "container_id": "a1b2c3d4e5f6...",
  "status": "running"
}
```

### 4. 配置并打开前端编辑器

1.  用代码编辑器打开 `frontend/index.html` 文件。
2.  找到以下这行代码：
    ```javascript
    const CONTAINER_ID = "07ca7e01ddd6"; // <--- 修改这里！
    ```
3.  将 `CONTAINER_ID` 的值替换为您在上一步中获得的 `container_id`。
4.  在浏览器中直接打开 `frontend/index.html` 文件。

现在，您应该能看到一个功能齐全的代码编辑器。当您修改代码时，它会自动调用后端进行 ESLint 检查，并在代码中实时显示错误和警告。

### 5. 停止并清理沙箱

完成开发后，使用以下命令停止并移除容器，释放资源。

```bash
# 将 {container_id} 替换为您的容器 ID
curl -X POST http://127.0.0.1:8000/sandbox/{container_id}/stop
```

## API 端点详解

所有端点均相对于 `http://127.0.0.1:8000`。

| 端点 | 方法 | 描述 |
| :--- | :--- | :--- |
| `/sandbox/start` | `POST` | 构建镜像（如果不存在）并启动一个新的沙箱容器。 |
| `/lint` | `POST` | 在指定容器内对 Vue 代码片段执行 ESLint 检查。 |
| `/sandbox/{id}/logs` | `GET` | 获取指定容器的最后 200 行日志。 |
| `/sandbox/{id}/stop` | `POST` | 停止并移除指定的沙箱容器。 |

## 贡献与调试

我们欢迎团队成员对这个工具进行改进。以下是一些有用的信息：

-   **ESLint 规则**：所有 ESLint 规则都硬编码在 `backend/app/main.py` 的 `lint_code` 函数中。要调整规则，请直接修改 `eslint_config` 字典。
-   **前端调试**：`frontend/index.html` 页面包含一个“调试静态检查”按钮。点击后会显示与后端通信的详细日志，包括原始请求和响应，非常适合用于排查问题。
-   **沙箱环境**：如果需要为沙箱添加新的 `npm` 依赖，请将其添加到 `hello-vue/package.json` 中，然后重新构建镜像（删除旧镜像或在启动时设置 `"build": true`）。

## 常见问题 (FAQ)

-   **Q: 点击“调试静态检查”后，响应显示 “Container not found”**
    A: 请检查 `frontend/index.html` 中的 `CONTAINER_ID` 是否正确，以及对应的 Docker 容器是否仍在运行。

-   **Q: 如何访问沙箱中运行的 Vue 应用？**
    A: 在启动沙箱时，我们已经将容器的 `5173` 端口映射到了主机的 `5173` 端口。您可以直接在浏览器中访问 `http://localhost:5173` 来查看实时效果。
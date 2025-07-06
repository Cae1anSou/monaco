# Vue Sandbox Manager

本项目是一个用于管理 Vue.js 开发沙箱的后端服务。它使用 FastAPI 构建，并通过 Docker API 来动态启动、监控和停止独立的 Vue.js 开发环境容器。

## 技术栈

-   **后端**: Python 3, FastAPI, Uvicorn
-   **前端 (沙箱)**: Vue 3, Vite
-   **容器化**: Docker

## 环境准备

在开始之前，请确保您的开发环境中已安装以下软件：

-   Python (3.8+ 版本)
-   Node.js (16+ 版本) 和 npm
-   Docker Desktop

## 安装与配置

1.  **克隆仓库**
    ```bash
    git clone <your-repo-url>
    cd <project-directory>
    ```

2.  **后端设置**
    进入后端目录，并安装所需的 Python 依赖。
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

3.  **前端依赖安装**
    前端代码位于 `hello-vue` 目录。后端服务会自动处理其 Docker 镜像的构建，但如果您需要独立修改或调试前端代码，可以先安装其依赖。
    ```bash
    cd hello-vue
    npm install
    cd ..
    ```

## 运行项目

1.  **启动 Docker**
    请确保您的 Docker Desktop 正在运行。

2.  **启动后端服务**
    在项目根目录的 `backend` 文件夹下，运行以下命令启动 FastAPI 服务：
    ```bash
    cd backend
    uvicorn app.main:app --reload --port 8000
    ```
    服务将在 `http://127.0.0.1:8000` 上运行。

## API 端点说明

您可以通过向后端服务发送 HTTP 请求来管理 Vue 沙箱。

---

### 1. 启动沙箱

启动一个新的 Vue.js 开发环境容器。服务会先检查是否存在对应的 Docker 镜像，如果不存在，会根据 `hello-vue` 目录中的 Dockerfile 自动构建。

-   **URL**: `/sandbox/start`
-   **方法**: `POST`
-   **请求体** (JSON):
    ```json
    {
        "name": "hello-vue",
        "path": "../hello-vue",
        "external_port": 5173,
        "internal_port": 5173,
        "build": true
    }
    ```
-   **成功响应**:
    ```json
    {
        "container_id": "a1b2c3d4e5f6...",
        "status": "running"
    }
    ```

---

### 2. 获取沙箱日志

查看指定容器的实时日志。

-   **URL**: `/sandbox/{container_id}/logs`
-   **方法**: `GET`
-   **URL 参数**:
    -   `container_id` (string, required): 容器的 ID。
    -   `tail` (int, optional, default: 200): 获取日志的最后行数。
-   **成功响应**:
    ```json
    {
        "logs": "..."
    }
    ```

---

### 3. 对代码进行 Lint 检查

在正在运行的容器内，对给定的 Vue 代码片段执行 ESLint 检查。

-   **URL**: `/lint`
-   **方法**: `POST`
-   **请求体** (JSON):
    ```json
    {
        "container_id": "a1b2c3d4e5f6...",
        "code": "<template>...</template><script>...</script>"
    }
    ```
-   **成功响应**:
    ```json
    {
        "lint_result": "[...ESLint JSON output...]"
    }
    ```

---

### 4. 停止并移除沙箱

停止并删除指定的容器。

-   **URL**: `/sandbox/{container_id}/stop`
-   **方法**: `POST`
-   **URL 参数**:
    -   `container_id` (string, required): 容器的 ID。
-   **成功响应**:
    ```json
    {
        "container_id": "a1b2c3d4e5f6...",
        "status": "stopped"
    }
    ```
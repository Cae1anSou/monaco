"""Minimal FastAPI backend to manage Vue sandbox containers.

Endpoints:
1. POST /sandbox/start  -> build image (if not built) & run container (detached)
   Request body: {"name": "hello-vue", "path": "../hello-vue"}
   Returns: {"container_id": "...", "status": "running"}

2. GET /sandbox/{container_id}/logs -> tail logs (last 200 lines)

3. POST /sandbox/{container_id}/stop -> stop and remove container

Note: In a real system you'd add auth, better error handling, log streaming via WebSocket, etc.
"""

import os
import json
import pathlib
import subprocess
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from docker import from_env as docker_from_env
from docker.models.containers import Container

app = FastAPI()

# 配置 CORS 中间件
# 为了调试，暂时允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)

app.title = "Vue Sandbox Manager"

docker_client = docker_from_env()

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent  # /monaco


class SandboxStartReq(BaseModel):
    name: str = "hello-vue"
    path: str = "hello-vue"  # relative to project root
    external_port: int = 5173
    internal_port: int = 5173
    build: bool = True  # whether to build image before run
    image_tar: Optional[str] = None  # relative path to prebuilt image tar, e.g. "hello-vue/hello-vue-image.tar"


@app.post("/sandbox/start")
async def start_sandbox(req: SandboxStartReq):
    image_tag = f"{req.name}:latest"

    # Build image if requested or if not exists
    def _image_exists(tag: str) -> bool:
        try:
            docker_client.images.get(tag)
            return True
        except Exception:
            return False

    # Ensure image is available: try existing, then load tar, else build
    if not _image_exists(image_tag):
        if req.image_tar:
            tar_path = PROJECT_ROOT / req.image_tar
            if not tar_path.exists():
                raise HTTPException(status_code=404, detail="image_tar file not found")
            try:
                with tar_path.open("rb") as f:
                    images = docker_client.images.load(f.read())
                # Tag the first loaded image so we have predictable tag
                if images:
                    images[0].tag(image_tag)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"docker load failed: {e}")
        elif req.build:
            context_path = PROJECT_ROOT / req.path
            if not context_path.exists():
                raise HTTPException(status_code=404, detail="Project path not found")
            build_cmd = [
                "docker", "build", "-t", image_tag, str(context_path)
            ]
            proc = subprocess.run(build_cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                raise HTTPException(status_code=500, detail=proc.stderr[-1000:])
        else:
            raise HTTPException(status_code=400, detail="Image not found and build disabled; provide image_tar or enable build")

    # Run container detached, remove on stop, map port
    container: Container = docker_client.containers.run(
        image_tag,
        detach=True,
        ports={f"{req.internal_port}/tcp": req.external_port},
        labels={"sandbox": req.name},
    )

    return {"container_id": container.id, "status": container.status}


@app.get("/sandbox/{container_id}/logs")
async def sandbox_logs(container_id: str, tail: int = 200):
    try:
        container = docker_client.containers.get(container_id)
        logs = container.logs(tail=tail).decode()
        return {"logs": logs}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


class LintCodeReq(BaseModel):
    container_id: str
    code: str


@app.post("/lint")
async def lint_code(req: LintCodeReq):
    try:
        container: Container = docker_client.containers.get(req.container_id)
        if container.status != 'running':
            raise HTTPException(status_code=400, detail="Container is not running.")

        import base64, shlex

        # 将代码内容编码为 base64，避免在 shell 中转义问题
        encoded = base64.b64encode(req.code.encode()).decode()
        
        # 创建增强的 ESLint 配置，使其类似 VSCode 体验
        # 添加 Vue 插件和规则，以检查块外内容和文件格式
        eslint_config = {
            "extends": [
                "eslint:recommended",
                "plugin:vue/vue3-recommended"
            ],
            "plugins": ["vue"],
            "parser": "vue-eslint-parser",
            "parserOptions": {
                "ecmaVersion": 2022,
                "sourceType": "module"
            },
            "rules": {
                "vue/valid-template-root": "error",  # 检查文档结构完整性
                "vue/comment-directive": ["error", {  # 检查指令注释
                    "reportUnusedDisableDirectives": True
                }],
                "vue/no-multiple-template-root": "error",  # 检查根元素唯一性
                "vue/no-unused-components": "error",     # 未使用组件检查
                "vue/no-unused-vars": "error",          # 未使用变量检查
                "vue/html-indent": ["error", 2],        # HTML缩进检查
                "vue/html-self-closing": "error",        # 自闭合标签检查
                "vue/no-irregular-whitespace": ["error", {  # 不规则空白检查
                    "skipStrings": False,
                    "skipComments": False,
                    "skipRegExps": False,
                    "skipTemplates": False,
                    "skipHTMLAttributeValues": False,
                    "skipHTMLTextContents": False
                }],
                "vue/no-parsing-error": "error",        # 解析错误检查
                "vue/no-template-shadow": "error",      # 模板阴影变量检查 
                # 使用新的块顺序规则替代已弃用的组件标签顺序规则
                "vue/block-order": ["error", {  
                    "order": ["template", "script", "style"]
                }]
                # 已移除不存在的规则：vue/no-multiple-top-level-tags
            }
        }
        
        # 将配置对象转换为JSON，然后base64编码
        eslint_config_encoded = base64.b64encode(json.dumps(eslint_config).encode()).decode()
        
        # 构造命令：先创建临时配置文件，然后使用该配置进行lint检查
        lint_cmd = (
            "sh -c "
            + shlex.quote(
                f"echo {eslint_config_encoded} | base64 -d > /tmp/.eslintrc.json && "
                f"ls -la /app/node_modules/eslint-plugin-vue || echo '插件目录不存在' && "
                f"echo '使用的NODE_PATH环境变量:' && echo $NODE_PATH && "
                f"echo '使用的配置文件:' && cat /tmp/.eslintrc.json && "
                f"echo {encoded} | base64 -d | NODE_PATH=/app/node_modules npx eslint --stdin --stdin-filename LintTarget.vue --format json --config /tmp/.eslintrc.json"
            )
        )
        
        # 检查容器是否安装了需要的依赖
        # 这部分是为了确保容器内有所需的eslint插件
        deps_check = "sh -c " + shlex.quote("npm list eslint-plugin-vue vue-eslint-parser || true")
        _, (deps_stdout, _) = container.exec_run(deps_check, workdir="/app", demux=True)
        deps_output = deps_stdout.decode() if deps_stdout else ""
        
        # 如果缺少依赖，尝试安装
        if "eslint-plugin-vue" not in deps_output or "vue-eslint-parser" not in deps_output:
            install_cmd = "sh -c " + shlex.quote("npm install --no-save eslint-plugin-vue vue-eslint-parser")
            container.exec_run(install_cmd, workdir="/app")

        # 执行lint命令
        exit_code, (stdout, stderr) = container.exec_run(lint_cmd, workdir="/app", demux=True)

        if stderr and stderr.strip():
            return {"lint_result": stderr.decode()}

        return {"lint_result": stdout.decode()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sandbox/{container_id}/stop")
async def stop_sandbox(container_id: str):
    try:
        container = docker_client.containers.get(container_id)
        container.stop()
        container.remove()
        return {"container_id": container_id, "status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

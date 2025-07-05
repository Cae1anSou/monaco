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
import pathlib
import subprocess
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from docker import from_env as docker_from_env
from docker.models.containers import Container

app = FastAPI(title="Vue Sandbox Manager")

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


@app.post("/sandbox/{container_id}/stop")
async def stop_sandbox(container_id: str):
    try:
        container = docker_client.containers.get(container_id)
        container.stop()
        container.remove()
        return {"container_id": container_id, "status": "stopped"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

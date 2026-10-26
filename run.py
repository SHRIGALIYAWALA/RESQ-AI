import os
from pathlib import Path
import subprocess

import uvicorn

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent
    os.chdir(project_root)
    frontend_root = project_root / "frontend-next"
    frontend_process = None

    if (frontend_root / "node_modules").is_dir():
        frontend_process = subprocess.Popen(["npm.cmd", "run", "dev"], cwd=frontend_root)
        print("Starting RESQ-AI command center...")
        print("Open this project link: http://localhost:3000/")
        print("Backend API is internal on port 8000; do not open it separately.")
    else:
        print("frontend-next/node_modules is missing; run npm install in frontend-next first.")
        print("Open http://localhost:8000/ for the backend fallback dashboard.")

    try:
        uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
    finally:
        if frontend_process is not None and frontend_process.poll() is None:
            frontend_process.terminate()
            frontend_process.wait(timeout=10)

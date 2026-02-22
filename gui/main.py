#!/usr/bin/env python3
"""
Codex Mission Control - GUI Backend
FastAPI + HTMX + Jinja2 for agent orchestration dashboard.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add harness directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from harnesscodex.config_loader import get_config, Config

app = FastAPI(
    title="Codex Mission Control",
    description="Agent orchestration dashboard for Codex Harness",
    version="2.0.0",
)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).parent.parent
HARNESS_DIR = BASE_DIR / "harnesscodex"
GUI_DIR = BASE_DIR / "gui"
STATIC_DIR = GUI_DIR / "static"
TEMPLATES_DIR = GUI_DIR / "templates"
LOGS_DIR = BASE_DIR / ".codex-logs"
QA_REPORTS_DIR = BASE_DIR / ".codex-qa-reports"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
QA_REPORTS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Global state for agent control
agent_state: Dict[str, Any] = {
    "status": "idle",  # idle, running, paused, error
    "current_role": None,
    "current_feature": None,
    "started_at": None,
    "logs": [],
    "audit_log": [],
}

# In-memory log buffer for streaming
log_buffer: List[str] = []
log_subscribers: List[Any] = []


def load_json_file(filename: str) -> Dict[str, Any]:
    """Load JSON file from harness directory."""
    path = HARNESS_DIR / filename
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json_file(filename: str, data: Dict[str, Any]) -> None:
    """Save JSON file to harness directory."""
    path = HARNESS_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_audit_log(action: str, details: Dict[str, Any]) -> None:
    """Add entry to audit log."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "details": details,
    }
    agent_state["audit_log"].append(entry)
    # Keep only last 100 entries
    if len(agent_state["audit_log"]) > 100:
        agent_state["audit_log"] = agent_state["audit_log"][-100:]


# Pydantic models for API
class TaskCreate(BaseModel):
    feature_id: str
    description: Optional[str] = None
    priority: Optional[str] = "normal"


class TaskUpdate(BaseModel):
    status: str


class AgentControl(BaseModel):
    action: str  # start, pause, resume, stop
    role: Optional[str] = None
    feature_id: Optional[str] = None


class MemoryQuery(BaseModel):
    query: str


# Routes

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    config = get_config()
    features = load_json_file("codex-features.json")
    queue = load_json_file("codex-task-queue.json")
    progress = load_json_file("codex-progress.json")
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "features": features,
        "queue": queue,
        "progress": progress,
        "agent_state": agent_state,
        "config": config.to_dict(),
    })


@app.get("/api/status", response_class=JSONResponse)
async def get_status():
    """Get current agent status."""
    queue = load_json_file("codex-task-queue.json")
    features = load_json_file("codex-features.json")
    
    return {
        "agent": agent_state,
        "queue": queue,
        "features": features,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/tasks", response_class=JSONResponse)
async def get_tasks():
    """Get all tasks."""
    queue = load_json_file("codex-task-queue.json")
    return queue


@app.post("/api/tasks", response_class=JSONResponse)
async def create_task(task: TaskCreate):
    """Create a new task."""
    queue = load_json_file("codex-task-queue.json")
    features = load_json_file("codex-features.json")
    
    # Check if feature exists
    feature_ids = [f.get("id") for f in features.get("features", [])]
    if task.feature_id not in feature_ids:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    # Add to queue
    new_task = {
        "feature_id": task.feature_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "priority": task.priority,
    }
    
    if "queue" not in queue:
        queue["queue"] = []
    queue["queue"].append(new_task)
    save_json_file("codex-task-queue.json", queue)
    
    add_audit_log("task_created", {"feature_id": task.feature_id})
    
    return {"status": "created", "task": new_task}


@app.patch("/api/tasks/{feature_id}", response_class=JSONResponse)
async def update_task(feature_id: str, update: TaskUpdate):
    """Update task status (with audit logging)."""
    queue = load_json_file("codex-task-queue.json")
    
    for task in queue.get("queue", []):
        if task.get("feature_id") == feature_id:
            old_status = task.get("status")
            task["status"] = update.status
            task["updated_at"] = datetime.now(timezone.utc).isoformat()
            save_json_file("codex-task-queue.json", queue)
            
            add_audit_log("task_updated", {
                "feature_id": feature_id,
                "old_status": old_status,
                "new_status": update.status,
            })
            
            return {"status": "updated", "task": task}
    
    raise HTTPException(status_code=404, detail="Task not found")


@app.post("/api/agent/control", response_class=JSONResponse)
async def control_agent(control: AgentControl):
    """Control agent execution (start, pause, resume, stop)."""
    if control.action == "start":
        agent_state["status"] = "running"
        agent_state["current_role"] = control.role
        agent_state["current_feature"] = control.feature_id
        agent_state["started_at"] = datetime.now(timezone.utc).isoformat()
        add_audit_log("agent_started", {"role": control.role, "feature_id": control.feature_id})
        
    elif control.action == "pause":
        if agent_state["status"] != "running":
            raise HTTPException(status_code=400, detail="Agent not running")
        agent_state["status"] = "paused"
        add_audit_log("agent_paused", {})
        
    elif control.action == "resume":
        if agent_state["status"] != "paused":
            raise HTTPException(status_code=400, detail="Agent not paused")
        agent_state["status"] = "running"
        add_audit_log("agent_resumed", {})
        
    elif control.action == "stop":
        agent_state["status"] = "idle"
        agent_state["current_role"] = None
        agent_state["current_feature"] = None
        add_audit_log("agent_stopped", {})
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    return {"status": agent_state["status"]}


@app.get("/api/logs/stream")
async def stream_logs():
    """Server-Sent Events for live log streaming."""
    async def event_generator():
        last_idx = 0
        while True:
            # Send new logs
            if len(log_buffer) > last_idx:
                for i in range(last_idx, len(log_buffer)):
                    yield f"data: {log_buffer[i]}\n\n"
                last_idx = len(log_buffer)
            await asyncio.sleep(0.1)
    
    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
    )


@app.get("/api/logs", response_class=JSONResponse)
async def get_logs(limit: int = 100):
    """Get recent logs."""
    log_files = list(LOGS_DIR.glob("*.log"))
    logs = []
    
    for log_file in sorted(log_files, reverse=True)[:5]:
        with open(log_file, "r") as f:
            content = f.readlines()[-limit:]
            logs.extend([{
                "file": log_file.name,
                "line": line.strip(),
            } for line in content])
    
    return {"logs": logs[-limit:]}


@app.get("/api/qa-reports", response_class=JSONResponse)
async def get_qa_reports():
    """List all QA reports."""
    reports = []
    for report_file in QA_REPORTS_DIR.glob("*.md"):
        stat = report_file.stat()
        reports.append({
            "name": report_file.name,
            "path": str(report_file),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return {"reports": reports}


@app.get("/api/qa-reports/{report_name}", response_class=JSONResponse)
async def get_qa_report(report_name: str):
    """Get specific QA report content."""
    report_path = QA_REPORTS_DIR / report_name
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    with open(report_path, "r") as f:
        content = f.read()
    
    return {"name": report_name, "content": content}


@app.post("/api/memory/query", response_class=JSONResponse)
async def query_memory(query: MemoryQuery):
    """Query Cognee memory layer."""
    config = get_config()
    
    if not config.cognee.enabled:
        return {"results": [], "error": "Cognee is disabled"}
    
    try:
        from harnesscodex.cognee_adapter import CogneeAdapter
        
        adapter = CogneeAdapter(persistence_dir=config.cognee.persistence_dir)
        results = await adapter.query(query.query)
        return {"results": results, "query": query.query}
        
    except ImportError:
        return {"results": [], "error": "Cognee not installed"}
    except Exception as e:
        return {"results": [], "error": str(e)}


@app.post("/api/memory/index", response_class=JSONResponse)
async def index_memory():
    """Index harness files into Cognee memory."""
    config = get_config()
    
    if not config.cognee.enabled:
        return {"status": "error", "message": "Cognee is disabled"}
    
    try:
        from harnesscodex.cognee_adapter import CogneeAdapter
        import glob
        
        adapter = CogneeAdapter(persistence_dir=config.cognee.persistence_dir)
        indexed_files = []
        
        for pattern in config.cognee.index_paths:
            for filepath in glob.glob(pattern):
                if os.path.exists(filepath):
                    with open(filepath, "r") as f:
                        content = f.read()
                    await adapter.add_text(content, dataset_name="project_memory")
                    indexed_files.append(filepath)
        
        return {"status": "success", "indexed_files": indexed_files}
        
    except ImportError:
        return {"status": "error", "message": "Cognee not installed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/config", response_class=JSONResponse)
async def get_config_api():
    """Get current configuration."""
    config = get_config()
    return config.to_dict()


@app.get("/api/audit-log", response_class=JSONResponse)
async def get_audit_log():
    """Get audit log entries."""
    return {"audit_log": agent_state["audit_log"]}


# HTMX partial routes

@app.get("/partials/task-list", response_class=HTMLResponse)
async def task_list_partial(request: Request):
    """HTMX partial for task list."""
    queue = load_json_file("codex-task-queue.json")
    return templates.TemplateResponse("partials/task_list.html", {
        "request": request,
        "queue": queue,
        "agent_state": agent_state,
    })


@app.get("/partials/feature-list", response_class=HTMLResponse)
async def feature_list_partial(request: Request):
    """HTMX partial for feature list."""
    features = load_json_file("codex-features.json")
    return templates.TemplateResponse("partials/feature_list.html", {
        "request": request,
        "features": features,
    })


@app.get("/partials/agent-status", response_class=HTMLResponse)
async def agent_status_partial(request: Request):
    """HTMX partial for agent status."""
    return templates.TemplateResponse("partials/agent_status.html", {
        "request": request,
        "agent_state": agent_state,
    })


@app.get("/partials/logs", response_class=HTMLResponse)
async def logs_partial(request: Request, limit: int = 50):
    """HTMX partial for logs display."""
    logs = (await get_logs(limit))["logs"]
    return templates.TemplateResponse("partials/logs.html", {
        "request": request,
        "logs": logs,
    })


# Health check

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    config = get_config()
    uvicorn.run(
        app,
        host=config.gui.host,
        port=config.gui.port,
        reload=config.gui.debug,
    )
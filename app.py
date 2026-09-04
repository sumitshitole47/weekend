"""
AeroTwin-3D Platform Web Server
Serves the original, high-resolution 3D Digital Twin viewer directly at root (/) and /static/index.html.
Includes White Clay mode, Vertical Height Gauge, AI Structural Completion wireframe/ghost skin, and Telemetry.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="AeroTwin-3D Platform Viewer",
    description="Single-Pass Drone 3D Reconstruction & AI Inpainting Web Twin",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
os.makedirs("data/colmap_output", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data/colmap_output", StaticFiles(directory="data/colmap_output"), name="colmap_output")


@app.get("/", response_class=HTMLResponse)
async def serve_root():
    view_path = "data/colmap_output/view_3d_model.html"
    if os.path.exists(view_path):
        with open(view_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>AeroTwin-3D Platform Viewer Running</h1>"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

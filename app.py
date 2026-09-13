"""
AeroTwin-3D Platform Web Server & Automated 3D Reconstruction API
Provides:
1. Multi-file upload interface (.mp4 video + .srt telemetry)
2. Input file duration & timestamp alignment validation
3. Automated end-to-end 3D reconstruction pipeline triggering with 100% manual pipeline parity
4. Real-time background task progress tracking (/api/status)
5. Interactive WebGL Digital Twin viewer at root (/)
"""
import glob
import json
import os
import shutil
import sys
import threading
import time

from fastapi import FastAPI, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pipeline.config import load_config
from pipeline.preprocessor import preprocess_drone_video
from pipeline.telemetry import parse_srt_telemetry_file
from pipeline.dynamic_reconstructor import reconstruct_dense_point_cloud_from_frames
from pipeline.mesh_inpainting import inpaint_and_mesh_occluded_surfaces
from pipeline.exporter import export_all_formats
from validators import validate_video_file, validate_telemetry_file, validate_video_srt_alignment

_src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
from generate_web_viewer import generate_web_viewer

app = FastAPI(
    title="AeroTwin-3D Platform & Reconstruction API",
    description="Automated Drone Video & SRT Telemetry 3D Digital Twin Generator (COLMAP)",
    version="3.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
os.makedirs("data/raw_video", exist_ok=True)
os.makedirs("data/frames", exist_ok=True)
os.makedirs("data/colmap_output/dense", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data/colmap_output", StaticFiles(directory="data/colmap_output"), name="colmap_output")

# Global pipeline execution state
PIPELINE_STATUS = {
    "status": "idle",       # "idle", "processing", "completed", "error"
    "progress": 0,          # 0 to 100
    "message": "Ready to upload drone video (.mp4) and flight telemetry (.srt)",
    "error": None,
    "metrics": None,
    "last_updated": time.time()
}

_pipeline_lock = threading.Lock()


def update_status(message: str, progress: int, status: str = "processing", error: str = None, metrics: dict = None):
    """Thread-safe update of pipeline execution status."""
    global PIPELINE_STATUS
    with _pipeline_lock:
        PIPELINE_STATUS["status"] = status
        PIPELINE_STATUS["progress"] = max(0, min(100, progress))
        PIPELINE_STATUS["message"] = message
        PIPELINE_STATUS["error"] = error
        if metrics:
            PIPELINE_STATUS["metrics"] = metrics
        PIPELINE_STATUS["last_updated"] = time.time()


def run_pipeline_worker(video_path: str, srt_path: str | None):
    """
    Background thread executing the EXACT 6-step function sequence as manual pipeline:
      1. Telemetry parsing & metric scale setup
      2. Frame extraction & Laplacian blur filtering
      3. GPU-Accelerated COLMAP SfM & Dense MVS
      4. Occlusion surface inpainting & structural metrics
      5. Multi-format deliverable exporter (OBJ, PLY, LAS, GeoTIFF, GLB, FBX)
      6. Master WebGL dashboard generation & display refresh
    """
    try:
        update_status("Initializing 3D reconstruction pipeline...", 5, "processing")

        # Step 1: Flight Telemetry & Metric Scaling Setup
        update_status("Step 1/6: Parsing SRT flight telemetry & computing GPS scale...", 10, "processing")
        if srt_path and os.path.exists(srt_path):
            try:
                records, disp_m, scale = parse_srt_telemetry_file(
                    srt_path=srt_path,
                    progress_callback=lambda msg, pct: update_status(f"Step 1/6: {msg}", 10 + int(pct * 0.05), "processing")
                )
                update_status(f"Step 1/6: Parsed {len(records)} GPS records ({disp_m:.1f}m flight path).", 15, "processing")
            except Exception as tel_err:
                print(f"[WARNING] Telemetry parsing warning: {tel_err}")
                update_status("Step 1/6: Telemetry warning — continuing with altitude defaults.", 15, "processing")
        else:
            parse_srt_telemetry_file(srt_path=None)
            update_status("Step 1/6: No SRT provided — using barometer altitude defaults.", 15, "processing")

        # Step 2: Keyframe Extraction & Motion Blur Filtering
        update_status("Step 2/6: Extracting keyframes & Laplacian blur filtering...", 20, "processing")
        frame_count = preprocess_drone_video(
            video_path=video_path,
            progress_callback=lambda msg, pct: update_status(f"Step 2/6: {msg}", 20 + int(pct * 0.2), "processing")
        )
        update_status(f"Step 2/6: Retained {frame_count} sharp keyframes.", 40, "processing")

        # Step 3: GPU COLMAP SfM & Dense MVS
        update_status("Step 3/6: GPU COLMAP SfM & PatchMatch MVS...", 45, "processing")
        metrics = reconstruct_dense_point_cloud_from_frames(
            progress_callback=lambda msg, pct: update_status(f"Step 3/6: {msg}", pct, "processing")
        )

        # Step 4: Occlusion Inpainting & Structural Metrics
        update_status("Step 4/6: Occlusion inpainting & structural metrics...", 92, "processing")
        try:
            inpaint_and_mesh_occluded_surfaces()
        except Exception as inp_err:
            print(f"[WARNING] Inpainting warning: {inp_err}")

        # Step 5: Multi-Format Deliverable Exporter
        update_status("Step 5/6: Exporting OBJ, PLY, LAS, GeoTIFF, GLB, FBX deliverables...", 95, "processing")
        try:
            exports = export_all_formats()
            print(f"[OK] Deliverables exported: {list(exports.keys())}")
        except Exception as exp_err:
            print(f"[WARNING] Exporter warning: {exp_err}")

        # Step 6: Master WebGL Dashboard Generation & Display Refresh
        update_status("Step 6/6: Regenerating Master WebGL 3D Dashboard...", 98, "processing")
        try:
            generate_web_viewer()
        except Exception as viewer_err:
            print(f"[WARNING] Web viewer generation warning: {viewer_err}")

        # Completed
        pts = metrics.get("total_3d_points", 0)
        reg = metrics.get("registered_frames", 0)
        total = metrics.get("total_frames", 0)
        reproj = metrics.get("refined_reprojection_error_px", 0)

        update_status(
            f"Reconstruction Complete! "
            f"{pts:,} dense 3D points. "
            f"{reg}/{total} frames registered. "
            f"Reproj error: {reproj:.4f} px.",
            100,
            status="completed",
            metrics=metrics
        )

    except Exception as e:
        import traceback
        err_msg = str(e)
        print(f"[PIPELINE ERROR] {err_msg}\n{traceback.format_exc()}")
        update_status(f"Pipeline Failed: {err_msg}", 0, status="error", error=err_msg)


@app.get("/", response_class=HTMLResponse)
async def serve_root():
    """Serves the primary web upload dashboard and viewer UI."""
    upload_ui_path = "static/index.html"
    if os.path.exists(upload_ui_path):
        with open(upload_ui_path, "r", encoding="utf-8") as f:
            return f.read()

    view_path = "data/colmap_output/view_3d_model.html"
    if os.path.exists(view_path):
        with open(view_path, "r", encoding="utf-8") as f:
            return f.read()

    return "<h1>AeroTwin-3D Web Upload & Reconstruction Platform</h1>"


@app.get("/api/status")
async def get_pipeline_status():
    """Returns current status and progress of background reconstruction job."""
    with _pipeline_lock:
        return PIPELINE_STATUS


@app.post("/api/upload")
async def handle_video_upload(
    video: UploadFile = File(...),
    srt: UploadFile = File(None)
):
    """
    Accepts video (.mp4) and optional SRT telemetry (.srt) files via web form upload.
    Validates files, verifies duration alignment, saves inputs, and triggers 3D reconstruction.
    """
    global PIPELINE_STATUS
    with _pipeline_lock:
        if PIPELINE_STATUS["status"] == "processing":
            raise HTTPException(
                status_code=400,
                detail="A reconstruction pipeline is currently running. Please wait for completion."
            )

    # 1. Format Validation
    validate_video_file(video)
    srt_provided = srt is not None and srt.filename and srt.filename.strip() != ""
    if srt_provided:
        validate_telemetry_file(srt)

    try:
        # Clear old frame directories for clean execution
        for d in ["data/frames", "data/frames/masks"]:
            if os.path.exists(d):
                for f in glob.glob(os.path.join(d, "frame_*.*")):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

        # Save uploaded video
        video_target = os.path.join("data/raw_video", "uploaded_video.mp4")
        with open(video_target, "wb") as buf:
            shutil.copyfileobj(video.file, buf)

        if os.path.getsize(video_target) == 0:
            os.remove(video_target)
            raise HTTPException(status_code=400, detail="Uploaded video file is empty (0 bytes).")

        # Save uploaded SRT (if provided)
        srt_target = os.path.join("data/raw_video", "uploaded_video.srt")
        actual_srt_path = None

        if srt_provided:
            with open(srt_target, "wb") as buf:
                shutil.copyfileobj(srt.file, buf)

            if os.path.getsize(srt_target) == 0:
                os.remove(srt_target)
                raise HTTPException(status_code=400, detail="Uploaded SRT telemetry file is empty (0 bytes).")

            # VALIDATE VIDEO & SRT TIMESTAMP DURATION ALIGNMENT
            validate_video_srt_alignment(video_target, srt_target)
            actual_srt_path = srt_target
        else:
            if os.path.exists(srt_target):
                os.remove(srt_target)

        # Trigger background reconstruction worker
        thread = threading.Thread(
            target=run_pipeline_worker,
            args=(video_target, actual_srt_path),
            daemon=True
        )
        thread.start()

        update_status("Files validated and uploaded. Triggering COLMAP 3D reconstruction...", 2, "processing")

        return {
            "success": True,
            "message": "Upload successful. Video and telemetry duration verified. Reconstruction triggered.",
            "video_filename": video.filename,
            "srt_filename": srt.filename if srt_provided else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")


@app.get("/api/viewer", response_class=HTMLResponse)
async def serve_viewer():
    """Serves the most recently generated 3D viewer HTML directly (no iframe caching issues)."""
    view_path = "data/colmap_output/view_3d_model.html"
    if os.path.exists(view_path):
        with open(view_path, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="3D viewer not yet generated. Run the pipeline first.")


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Allows downloading resulting 3D models and JSON metric reports."""
    safe_name = os.path.basename(filename)
    candidates = [
        os.path.join("data/colmap_output/dense", safe_name),
        os.path.join("data/colmap_output", safe_name),
        os.path.join("data/raw_video", safe_name),
    ]
    for c in candidates:
        if os.path.exists(c):
            return FileResponse(c, filename=safe_name)

    raise HTTPException(status_code=404, detail=f"Requested file '{safe_name}' not found.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

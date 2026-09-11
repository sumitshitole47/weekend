"""
AeroTwin-3D Platform Web Server & Automated 3D Reconstruction API
Provides:
1. Multi-file upload interface (.mp4 video + .srt telemetry)
2. Input file validation & automatic file placement
3. Automated end-to-end 3D reconstruction pipeline triggering (real COLMAP)
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
from pipeline.inpainting import run_ai_occlusion_inpainting

app = FastAPI(
    title="AeroTwin-3D Platform & Reconstruction API",
    description="Automated Drone Video & SRT Telemetry 3D Digital Twin Generator (COLMAP)",
    version="3.0.0"
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
    Background thread executing the full COLMAP reconstruction pipeline.

    Steps:
      1. Video preprocessing (frame extraction + blur filtering)
      2. SRT telemetry parsing (skipped gracefully if srt_path is None or missing)
      3. COLMAP reconstruction (feature extraction → SfM → MVS → Poisson mesh)
      4. AI occlusion inpainting
      5. Web viewer HTML generation from real PLY output
    """
    try:
        update_status("Starting 3D reconstruction pipeline...", 5, "processing")

        # ------------------------------------------------------------------
        # Step 1: Preprocess video frames
        # ------------------------------------------------------------------
        update_status("Extracting 2.5 FPS keyframes & filtering blurry frames...", 10, "processing")
        frame_count = preprocess_drone_video(
            video_path=video_path,
            progress_callback=lambda msg, pct: update_status(msg, 10 + int(pct * 0.3), "processing")
        )
        update_status(f"Extracted {frame_count} sharp keyframes.", 40, "processing")

        # ------------------------------------------------------------------
        # Step 2: Parse telemetry (optional — skip cleanly if no SRT)
        # ------------------------------------------------------------------
        if srt_path and os.path.exists(srt_path):
            update_status("Parsing SRT telemetry & computing GPS metric scaling...", 42, "processing")
            try:
                records, disp_m, scale = parse_srt_telemetry_file(
                    srt_path=srt_path,
                    progress_callback=lambda msg, pct: update_status(msg, 42 + int(pct * 0.05), "processing")
                )
                update_status(
                    f"Telemetry parsed: {len(records)} GPS records, {disp_m:.1f} m flight path.",
                    47, "processing"
                )
            except Exception as tel_err:
                print(f"[WARNING] Telemetry parsing failed (non-fatal): {tel_err}")
                update_status("Telemetry parse warning — continuing with altitude defaults.", 47, "processing")
        else:
            print("[INFO] No SRT telemetry uploaded. Using default altitude from config.")
            update_status("No SRT provided — using config altitude defaults.", 47, "processing")

        # ------------------------------------------------------------------
        # Step 3: COLMAP 3D reconstruction
        # ------------------------------------------------------------------
        update_status("Running COLMAP: Feature extraction (16,384 SIFT/frame)...", 50, "processing")
        metrics = reconstruct_dense_point_cloud_from_frames(
            progress_callback=lambda msg, pct: update_status(msg, pct, "processing")
        )

        # ------------------------------------------------------------------
        # Step 4: AI occlusion inpainting
        # ------------------------------------------------------------------
        update_status("Running AI occlusion inpainting for unseen rear facades...", 92, "processing")
        try:
            run_ai_occlusion_inpainting(
                progress_callback=lambda msg, pct: update_status(msg, 92 + int(pct * 0.03), "processing")
            )
        except Exception as inp_err:
            print(f"[WARNING] Inpainting step failed (non-fatal): {inp_err}")

        # ------------------------------------------------------------------
        # Step 5: Generate WebGL viewer HTML from real PLY output
        # ------------------------------------------------------------------
        update_status("Generating WebGL 3D viewer from reconstruction output...", 95, "processing")
        try:
            src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
            if src_dir not in sys.path:
                sys.path.insert(0, src_dir)
            from generate_web_viewer import generate_web_viewer
            generate_web_viewer()
        except Exception as viewer_err:
            print(f"[WARNING] Web viewer generation failed: {viewer_err}")
            update_status(f"Viewer generation warning: {viewer_err}", 95, "processing")

        # ------------------------------------------------------------------
        # Done
        # ------------------------------------------------------------------
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
    Validates files, saves to pipeline inputs, and triggers COLMAP 3D reconstruction.
    """
    global PIPELINE_STATUS
    with _pipeline_lock:
        if PIPELINE_STATUS["status"] == "processing":
            raise HTTPException(
                status_code=400,
                detail="A reconstruction pipeline is currently running. Please wait for completion."
            )

    # 1. Validate Video File
    if not video or not video.filename:
        raise HTTPException(status_code=400, detail="No video file provided.")

    v_ext = os.path.splitext(video.filename)[1].lower()
    allowed_v_exts = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    if v_ext not in allowed_v_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video format '{v_ext}'. Allowed: {', '.join(allowed_v_exts)}"
        )

    # 2. Validate SRT File (if provided)
    srt_provided = srt is not None and srt.filename and srt.filename.strip() != ""
    if srt_provided:
        s_ext = os.path.splitext(srt.filename)[1].lower()
        if s_ext != ".srt":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid telemetry format '{s_ext}'. Telemetry must be a .srt file."
            )

    try:
        # Clear old keyframe directories for clean processing
        frames_dir = "data/frames"
        masks_dir = "data/frames/masks"
        for d in [frames_dir, masks_dir]:
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

        # Save uploaded SRT (only if provided and non-empty)
        srt_target = os.path.join("data/raw_video", "uploaded_video.srt")
        actual_srt_path = None

        if srt_provided:
            with open(srt_target, "wb") as buf:
                shutil.copyfileobj(srt.file, buf)

            if os.path.getsize(srt_target) == 0:
                os.remove(srt_target)
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded SRT telemetry file is empty (0 bytes)."
                )
            actual_srt_path = srt_target
        else:
            # Remove any stale SRT from a previous run so it's not mistakenly used
            if os.path.exists(srt_target):
                os.remove(srt_target)

        # Trigger background pipeline
        thread = threading.Thread(
            target=run_pipeline_worker,
            args=(video_target, actual_srt_path),
            daemon=True
        )
        thread.start()

        update_status("Files uploaded. Launching COLMAP 3D reconstruction pipeline...", 2, "processing")

        return {
            "success": True,
            "message": "Upload successful. COLMAP 3D reconstruction pipeline triggered.",
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

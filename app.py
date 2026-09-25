import os
import time
import glob
import shutil
import asyncio
import traceback
import threading
from typing import Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from pipeline.telemetry import parse_srt_telemetry_file
from pipeline.preprocessor import preprocess_drone_video
from pipeline.dynamic_reconstructor import reconstruct_dense_point_cloud_from_frames
from pipeline.mesh_inpainting import inpaint_and_mesh_occluded_surfaces
from pipeline.exporter import export_all_formats
from src.generate_web_viewer import generate_web_viewer

app = FastAPI(
    title="AeroTwin-3D Platform & Reconstruction API",
    description="Automated Drone Video & SRT Telemetry 3D Digital Twin Generator",
    version="3.0.0",
)

os.makedirs("static", exist_ok=True)
os.makedirs("data/raw_video", exist_ok=True)
os.makedirs("data/colmap_output/dense", exist_ok=True)
os.makedirs("data/colmap_output/exports", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

def get_initial_status() -> Dict[str, Any]:
    out_ply = "data/colmap_output/exports/aerotwin_model.ply"
    if not os.path.exists(out_ply):
        out_ply = "data/colmap_output/dense/fused_corrected.ply"
    
    if os.path.exists(out_ply) and os.path.getsize(out_ply) > 1000:
        metrics = {}
        metrics_file = "data/colmap_output/building_metrics.json"
        if os.path.exists(metrics_file):
            try:
                import json
                with open(metrics_file, "r", encoding="utf-8") as f:
                    metrics = json.load(f)
            except Exception:
                pass
        return {
            "status": "completed",
            "progress": 100,
            "message": "3D Digital Twin Loaded",
            "error": None,
            "metrics": metrics,
            "model_url": "/api/model/current.ply",
            "timestamp": time.time()
        }
    return {
        "status": "idle",
        "progress": 0,
        "message": "Ready to upload drone video (.mp4) and flight telemetry (.srt)",
        "error": None,
        "metrics": None,
        "model_url": None,
        "timestamp": time.time()
    }

current_status: Dict[str, Any] = get_initial_status()

def update_status(message: str, progress: int, status: str = "processing", error: Optional[str] = None, metrics: Optional[dict] = None, model_url: Optional[str] = None):
    global current_status
    current_status = {
        "status": status,
        "progress": progress,
        "message": message,
        "error": error,
        "metrics": metrics,
        "model_url": model_url,
        "timestamp": time.time()
    }
    print(f"[{progress:3d}%] [{status.upper()}] {message}", flush=True)

def purge_stale_outputs():
    # Deletes all previous run deliverables and temporary 3D outputs to prevent accidental cache fallbacks
    patterns = [
        "data/frames/*",
        "data/colmap_output/sparse/*",
        "data/colmap_output/dense/*",
        "data/colmap_output/exports/*",
        "data/colmap_output/colmap/*",
        "data/colmap_output/*.html",
        "data/colmap_output/*.json",
        "static/models/*"
    ]
    deleted_count = 0
    for p in patterns:
        for path in glob.glob(p):
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    os.remove(path)
                    deleted_count += 1
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    deleted_count += 1
            except Exception as e:
                print(f"[PURGE WARNING] Could not remove '{path}': {e}", flush=True)
    print(f"[OK] Purged {deleted_count} stale output files before new run.", flush=True)

def validate_video_srt_alignment(video_path: str, srt_path: Optional[str]) -> bool:
    if not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="Video file missing on server.")
    if os.path.getsize(video_path) == 0:
        raise HTTPException(status_code=400, detail="Uploaded video file is empty (0 bytes).")
    return True

def run_pipeline_worker(video_path: str, srt_path: Optional[str]):
    try:
        v_abs = os.path.abspath(video_path)
        v_size = os.path.getsize(video_path) if os.path.exists(video_path) else 0
        v_mtime = time.ctime(os.path.getmtime(video_path)) if os.path.exists(video_path) else "N/A"
        s_abs = os.path.abspath(srt_path) if (srt_path and os.path.exists(srt_path)) else "None (Barometer Fallback)"

        print("=" * 80, flush=True)
        print("[AeroTwin-3D] [START] PERMANENT LOG: RECONSTRUCTION RUN STARTING", flush=True)
        print(f"   INPUT VIDEO PATH : {v_abs} | EXISTS: {os.path.exists(video_path)}", flush=True)
        print(f"   INPUT VIDEO SIZE : {v_size:,} bytes", flush=True)
        print(f"   INPUT VIDEO MTIME: {v_mtime}", flush=True)
        print(f"   INPUT TELEMETRY  : {s_abs}", flush=True)
        print("=" * 80, flush=True)

        update_status("Initializing 3D reconstruction pipeline...", 5, "processing")

        # Step 1: Telemetry Parsing
        update_status("Step 1/6: Parsing SRT flight telemetry & computing GPS scale...", 10, "processing")
        if srt_path and os.path.exists(srt_path):
            try:
                records, disp_m, scale = parse_srt_telemetry_file(
                    srt_path=srt_path,
                    progress_callback=lambda msg, pct: update_status(f"Step 1/6: {msg}", 10 + int(pct * 0.05), "processing")
                )
                update_status(f"Step 1/6: Parsed {len(records)} GPS records ({disp_m:.1f}m flight path).", 15, "processing")
            except Exception as tel_err:
                print(f"[WARNING] Telemetry parsing warning: {tel_err}", flush=True)
                update_status("Step 1/6: Telemetry warning  continuing with altitude defaults.", 15, "processing")
        else:
            parse_srt_telemetry_file(srt_path=None)
            update_status("Step 1/6: No SRT provided  using barometer altitude defaults.", 15, "processing")

        # Step 2: Keyframe Extraction
        update_status("Step 2/6: Extracting keyframes & Laplacian blur filtering...", 20, "processing")
        frame_count = preprocess_drone_video(
            video_path=video_path,
            progress_callback=lambda msg, pct: update_status(f"Step 2/6: {msg}", 20 + int(pct * 0.2), "processing")
        )
        if frame_count == 0:
            raise RuntimeError("Keyframe extraction failed: 0 valid frames extracted from video.")
        update_status(f"Step 2/6: Retained {frame_count} sharp keyframes.", 40, "processing")

        # Step 3: GPU COLMAP SfM & Dense MVS
        update_status("Step 3/6: GPU COLMAP SfM & PatchMatch MVS...", 45, "processing")
        metrics = reconstruct_dense_point_cloud_from_frames(
            progress_callback=lambda msg, pct: update_status(f"Step 3/6: {msg}", pct, "processing")
        )

        pts = metrics.get("total_3d_points", 0)
        reg = metrics.get("registered_frames", 0)
        total = metrics.get("total_frames", 0)
        reproj = metrics.get("refined_reprojection_error_px", 0)

        # STRICT ERROR CHECK: Raise Exception if COLMAP failed to produce 3D points
        if pts == 0 or reg == 0:
            raise RuntimeError(f"COLMAP 3D Reconstruction Failed: {reg}/{total} frames registered, {pts} dense 3D points generated.")

        # Step 4: Inpainting
        update_status("Step 4/6: Occlusion inpainting & structural metrics...", 92, "processing")
        try:
            inpaint_and_mesh_occluded_surfaces()
        except Exception as inp_err:
            print(f"[WARNING] Inpainting warning: {inp_err}", flush=True)

        # Step 5: Deliverable Exporter
        update_status("Step 5/6: Exporting OBJ, PLY, LAS, GeoTIFF, GLB, FBX deliverables...", 95, "processing")
        try:
            exports = export_all_formats()
            print(f"[OK] Deliverables exported: {list(exports.keys())}", flush=True)
        except Exception as exp_err:
            print(f"[WARNING] Exporter warning: {exp_err}", flush=True)

        # Step 6: Master WebGL Dashboard Generation
        update_status("Step 6/6: Regenerating Master WebGL 3D Dashboard...", 98, "processing")
        try:
            generate_web_viewer()
        except Exception as viewer_err:
            print(f"[WARNING] Web viewer generation warning: {viewer_err}", flush=True)

        # PERMANENT OPERATIONAL COMPLETION LOG
        out_ply = os.path.abspath("data/colmap_output/exports/aerotwin_model.ply")
        if not os.path.exists(out_ply):
            out_ply = os.path.abspath("data/colmap_output/dense/fused_corrected.ply")
        out_size = os.path.getsize(out_ply) if os.path.exists(out_ply) else 0
        out_mtime = time.ctime(os.path.getmtime(out_ply)) if os.path.exists(out_ply) else "N/A"

        print("=" * 80, flush=True)
        print("[AeroTwin-3D] [SUCCESS] PERMANENT LOG: RECONSTRUCTION RUN COMPLETED SUCCESSFULLY", flush=True)
        print(f"   OUTPUT PLY PATH  : {out_ply} | EXISTS: {os.path.exists(out_ply)}", flush=True)
        print(f"   OUTPUT PLY SIZE  : {out_size:,} bytes", flush=True)
        print(f"   OUTPUT PLY MTIME : {out_mtime}", flush=True)
        print("=" * 80, flush=True)

        update_status(
            f"Reconstruction Complete! {pts:,} dense 3D points. {reg}/{total} frames registered. Reproj error: {reproj:.4f} px.",
            100,
            status="completed",
            model_url="/api/model/current.ply",
            metrics=metrics
        )

    except Exception as e:
        err_msg = str(e)
        print(f"[PIPELINE ERROR] {err_msg}\n{traceback.format_exc()}", flush=True)
        update_status(f"Pipeline Failed: {err_msg}", 0, status="error", error=err_msg)


@app.get("/", response_class=HTMLResponse)
async def serve_root():
    upload_ui_path = "static/index.html"
    if os.path.exists(upload_ui_path):
        with open(upload_ui_path, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="Primary dashboard index.html not found.")


@app.get("/api/status")
async def get_status():
    return JSONResponse(content=current_status)


@app.get("/api/metrics")
async def get_metrics():
    metrics_path = "data/colmap_output/building_metrics.json"
    if os.path.exists(metrics_path):
        try:
            import json
            with open(metrics_path, "r", encoding="utf-8") as f:
                return JSONResponse(content=json.load(f))
        except Exception:
            pass
    return JSONResponse(content={})


@app.get("/api/telemetry")
async def get_telemetry():
    telemetry_path = "data/colmap_output/telemetry.json"
    if os.path.exists(telemetry_path):
        try:
            import json
            with open(telemetry_path, "r", encoding="utf-8") as f:
                return JSONResponse(content=json.load(f))
        except Exception:
            pass
    return JSONResponse(content=[])


@app.get("/api/accuracy")
async def get_accuracy_report():
    acc_path = "data/colmap_output/accuracy_report.json"
    if os.path.exists(acc_path):
        try:
            import json
            with open(acc_path, "r", encoding="utf-8") as f:
                return JSONResponse(content=json.load(f))
        except Exception:
            pass
    return JSONResponse(content={})


@app.get("/api/model/current.ply")
async def serve_current_ply():
    # Serves the latest reconstructed 3D PLY model deliverable dynamically with strict no-cache headers
    candidates = [
        "data/colmap_output/exports/aerotwin_model.ply",
        "data/colmap_output/dense/fused_corrected.ply",
        "data/colmap_output/dense/fused.ply",
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 300:
            return FileResponse(
                c,
                media_type="application/octet-stream",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    raise HTTPException(status_code=404, detail="No valid 3D PLY model found for current reconstruction run.")


@app.post("/api/upload")
async def upload_files_and_trigger_pipeline(
    video: Optional[UploadFile] = File(None),
    srt: Optional[UploadFile] = File(None)
):
    print("### RECONSTRUCTION ENDPOINT HIT ###", flush=True)
    video_target = "data/raw_video/uploaded_video.mp4"
    valid_video_exts = (".mp4", ".mov", ".avi", ".mkv")

    if video is not None and video.filename:
        if not any(video.filename.lower().endswith(ext) for ext in valid_video_exts):
            raise HTTPException(status_code=400, detail="Only video files (.mp4, .mov, .avi, .mkv) are accepted.")
        purge_stale_outputs()
        with open(video_target, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        video_name = video.filename
    else:
        # Fallback to existing server video file
        if os.path.exists(video_target) and os.path.getsize(video_target) > 0:
            video_name = "uploaded_video.mp4 (Cached)"
            purge_stale_outputs()
        else:
            mp4s = [f for f in glob.glob("data/raw_video/*.mp4") if os.path.getsize(f) > 0]
            if mp4s:
                video_target = mp4s[0]
                video_name = os.path.basename(video_target)
                purge_stale_outputs()
            else:
                raise HTTPException(status_code=400, detail="No video file uploaded and no default video found on server. Please select a .mp4 video.")

    srt_provided = False
    srt_target = "data/raw_video/uploaded_video.srt"
    actual_srt_path = None

    if srt is not None and srt.filename:
        if not srt.filename.lower().endswith(".srt"):
            raise HTTPException(status_code=400, detail="Only .srt telemetry files are accepted.")
        with open(srt_target, "wb") as buffer:
            shutil.copyfileobj(srt.file, buffer)

        if os.path.getsize(srt_target) > 0:
            srt_provided = True
            validate_video_srt_alignment(video_target, srt_target)
            actual_srt_path = srt_target
    else:
        matching_srt = video_target.rsplit(".", 1)[0] + ".srt"
        if os.path.exists(srt_target) and os.path.getsize(srt_target) > 0:
            actual_srt_path = srt_target
            srt_provided = True
        elif os.path.exists(matching_srt) and os.path.getsize(matching_srt) > 0:
            actual_srt_path = matching_srt
            srt_provided = True

    thread = threading.Thread(
        target=run_pipeline_worker,
        args=(video_target, actual_srt_path),
        daemon=True
    )
    thread.start()

    update_status("Reconstruction triggered. Initializing COLMAP pipeline...", 2, "processing")

    return {
        "success": True,
        "message": "Reconstruction triggered.",
        "video_filename": video_name,
        "srt_filename": os.path.basename(actual_srt_path) if srt_provided and actual_srt_path else None
    }


@app.get("/api/download/{filename}")
async def download_export_file(filename: str):
    safe_name = os.path.basename(filename)
    candidates = [
        os.path.join("data/colmap_output/exports", safe_name),
        os.path.join("data/colmap_output/dense", safe_name),
        os.path.join("data/colmap_output", safe_name)
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.getsize(c) > 0:
            return FileResponse(
                c,
                filename=safe_name,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
    raise HTTPException(status_code=404, detail=f"Deliverable file '{safe_name}' not found for current run.")

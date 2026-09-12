"""
AeroTwin-3D Master Pipeline Execution Engine (SIH26158 / NTRO)
Single-Pass Drone Video to Accurate 3D Model Generation System.

All benchmark requirements & parameters read from config.yaml.
Pipeline Flow:
  1. Telemetry & Metric Altitude Ingestion (<= 1m accuracy target)
  2. Frame Extraction & Blur Filtering (< 15 min execution target)
  3. GPU-Accelerated COLMAP SfM & Dense MVS
  4. Occlusion Surface Inpainting & Structural Metrics
  5. Multi-Format Deliverable Exporter (OBJ, PLY, LAS, GeoTIFF, GLB, FBX)
  6. WebGL Dashboard & Web Server Update
"""
import argparse
import os
import sys

_src_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_src_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pipeline.config import load_config
from pipeline.preprocessor import preprocess_drone_video
from pipeline.telemetry import parse_srt_telemetry_file
from pipeline.dynamic_reconstructor import reconstruct_dense_point_cloud_from_frames
from pipeline.mesh_inpainting import inpaint_and_mesh_occluded_surfaces
from pipeline.exporter import export_all_formats

os.chdir(_project_root)

def run_full_pipeline(
    video_path: str = None,
    srt_path: str = None,
):
    cfg = load_config()
    paths_cfg = cfg.get("output_paths", {})

    video_path = video_path or os.path.join(paths_cfg.get("raw_video_dir", "data/raw_video"), "uploaded_video.mp4")
    srt_path = srt_path or os.path.join(paths_cfg.get("raw_video_dir", "data/raw_video"), "uploaded_video.srt")

    print("=" * 75)
    print("🛸 AeroTwin-3D (SIH26158 / NTRO) Single-Pass 3D Reconstruction Pipeline")
    print(f"    Video Input  : {video_path}")
    print(f"    SRT Telemetry: {srt_path}")
    print(f"    Config Path  : {os.path.join(_project_root, 'config.yaml')}")

    import subprocess
    try:
        smi = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, check=True
        )
        gpu_details = smi.stdout.strip()
        print(f"    CUDA Hardware: {gpu_details} (GPU Index 0 Active)")
    except Exception as e:
        print(f"    GPU Status Notice: {e}")
    print("=" * 75)

    # Step 1: Telemetry Parsing & Scale Setup
    print("\n[Step 1/6] Ingesting Flight Telemetry & Altitude Scale Baseline")
    if os.path.exists(srt_path):
        try:
            records, disp_m, scale = parse_srt_telemetry_file(srt_path=srt_path)
            print(f"  Parsed {len(records)} GPS records. Total flight path: {disp_m:.1f} m. Scale: {scale:.3f}")
        except Exception as e:
            print(f"  [WARNING] Telemetry parsing warning: {e}")
    else:
        print(f"  [INFO] SRT file '{srt_path}' not found. Using relative barometer telemetry defaults.")

    # Step 2: Keyframe Extraction & Blur Filtering
    print("\n[Step 2/6] Frame Extraction & Laplacian Blur Filtering")
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file '{video_path}' not found.")
        sys.exit(1)

    frame_count = preprocess_drone_video(video_path=video_path)
    if frame_count == 0:
        print("[ERROR] No valid keyframes extracted.")
        sys.exit(1)
    print(f"  Extracted {frame_count} sharp keyframes at 2.0 FPS.")

    # Step 3: GPU COLMAP SfM & Dense MVS
    print("\n[Step 3/6] GPU-Accelerated COLMAP SfM & Dense PatchMatch MVS")
    try:
        metrics = reconstruct_dense_point_cloud_from_frames()
        print(f"  Reconstruction complete:")
        print(f"    Dense Points    : {metrics.get('total_3d_points', 0):,}")
        print(f"    Registered Frames: {metrics.get('registered_frames', 0)}/{metrics.get('total_frames', 0)}")
        print(f"    Reprojection Error: {metrics.get('refined_reprojection_error_px', 0):.4f} px")
    except Exception as e:
        print(f"[ERROR] Reconstruction failed: {e}")
        sys.exit(1)

    # Step 4: Occlusion Inpainting & Structural Metrics
    print("\n[Step 4/6] Occlusion Surface Inpainting & Structural Metrics")
    try:
        inpaint_and_mesh_occluded_surfaces()
    except Exception as e:
        print(f"  [WARNING] Inpainting step warning: {e}")

    # Step 5: Multi-Format Deliverable Export
    print("\n[Step 5/6] Multi-Format Deliverable Exporter (OBJ, PLY, LAS, GeoTIFF, GLB, FBX)")
    try:
        exports = export_all_formats()
        print(f"  Exported formats: {list(exports.keys())}")
    except Exception as e:
        print(f"  [WARNING] Deliverable export warning: {e}")

    # Step 6: WebGL Dashboard HTML Generation
    print("\n[Step 6/6] Regenerating Master WebGL 3D Dashboard")
    try:
        sys.path.insert(0, _src_dir)
        from generate_web_viewer import generate_web_viewer
        generate_web_viewer()
        print("  Master WebGL dashboard live at: data/colmap_output/view_3d_model.html & static/index.html")
    except Exception as e:
        print(f"  [WARNING] Web viewer generation warning: {e}")

    print("\n" + "=" * 75)
    print("✅ AeroTwin-3D Master Pipeline Execution Finished Successfully!")
    print("   Open http://localhost:8000 in your browser to view the 3D model.")
    print("=" * 75)

def main():
    parser = argparse.ArgumentParser(description="Run AeroTwin-3D Master Pipeline.")
    parser.add_argument("--video", type=str, default=None, help="Drone video path")
    parser.add_argument("--srt", type=str, default=None, help="Drone SRT path")
    args = parser.parse_args()
    run_full_pipeline(video_path=args.video, srt_path=args.srt)

if __name__ == "__main__":
    main()

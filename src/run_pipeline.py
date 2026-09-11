"""
AeroTwin-3D CLI Pipeline Runner
Reads all defaults from config.yaml (single source of truth).
Executes the same pipeline stages as the web app (app.py).

Usage:
  python src/run_pipeline.py
  python src/run_pipeline.py --video data/raw_video/my_flight.mp4 --srt data/raw_video/my_flight.srt
"""
import argparse
import os
import sys

# Allow running from src/ or from project root
_src_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_src_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pipeline.config import load_config
from pipeline.preprocessor import preprocess_drone_video
from pipeline.telemetry import parse_srt_telemetry_file
from pipeline.dynamic_reconstructor import reconstruct_dense_point_cloud_from_frames
from pipeline.inpainting import run_ai_occlusion_inpainting

# Always run from project root so relative data/ paths work
os.chdir(_project_root)


def run_full_pipeline(
    video_path: str = None,
    srt_path: str = None,
):
    """
    Master single-pass drone 3D reconstruction pipeline.

    All quality parameters are read from config.yaml.
    Steps:
      1. SRT telemetry parsing
      2. Video frame extraction + blur filtering
      3. COLMAP SfM + dense MVS reconstruction
      4. AI occlusion inpainting
      5. Web viewer HTML generation
    """
    cfg = load_config()
    paths_cfg = cfg.get("output_paths", {})

    video_path = video_path or os.path.join(paths_cfg.get("raw_video_dir", "data/raw_video"), "uploaded_video.mp4")
    srt_path = srt_path or os.path.join(paths_cfg.get("raw_video_dir", "data/raw_video"), "uploaded_video.srt")
    frames_dir = paths_cfg.get("frames_dir", "data/frames")
    colmap_dir = paths_cfg.get("colmap_dir", "data/colmap_output")

    print("=" * 70)
    print("[+] AeroTwin-3D Single-Pass Reconstruction Pipeline (CLI)")
    print(f"    Video  : {video_path}")
    print(f"    SRT    : {srt_path}")
    print(f"    Config : {os.path.join(_project_root, 'config.yaml')}")
    
    # Check CUDA GPU Availability via nvidia-smi
    import subprocess
    try:
        smi = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, check=True
        )
        gpu_details = smi.stdout.strip()
        print(f"    CUDA GPU: {gpu_details} (CUDA GPU 0 Active)")
    except Exception as e:
        print(f"    GPU Check Notice: {e}")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Step 1: Parse SRT telemetry
    # ------------------------------------------------------------------
    print("\n[Step 1/5] Telemetry Ingestion")
    if os.path.exists(srt_path):
        try:
            records, disp_m, scale = parse_srt_telemetry_file(srt_path=srt_path)
            print(f"  Parsed {len(records)} telemetry records. "
                  f"Flight path: {disp_m:.1f} m. Scale: {scale:.3f}")
        except Exception as e:
            print(f"  [WARNING] Failed to parse SRT telemetry: {e}")
    else:
        print(f"  [INFO] SRT file '{srt_path}' not found. Skipping telemetry parsing.")

    # ------------------------------------------------------------------
    # Step 2: Video preprocessing (frame extraction + blur filter)
    # ------------------------------------------------------------------
    print("\n[Step 2/5] Frame Extraction & Blur Filtering")
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file '{video_path}' not found.")
        sys.exit(1)

    frame_count = preprocess_drone_video(video_path=video_path)
    if frame_count == 0:
        print("[ERROR] No frames extracted from video.")
        sys.exit(1)
    print(f"  Extracted {frame_count} sharp keyframes.")

    # ------------------------------------------------------------------
    # Step 3: COLMAP 3D reconstruction
    # ------------------------------------------------------------------
    print("\n[Step 3/5] COLMAP 3D Reconstruction")
    try:
        metrics = reconstruct_dense_point_cloud_from_frames()
        print(f"\n  Reconstruction complete:")
        print(f"    Dense points   : {metrics.get('total_3d_points', 0):,}")
        print(f"    Registered frames: {metrics.get('registered_frames', 0)}/{metrics.get('total_frames', 0)}")
        print(f"    Reproj error   : {metrics.get('refined_reprojection_error_px', 0):.4f} px")
    except Exception as e:
        print(f"[ERROR] Reconstruction failed: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Step 4: AI occlusion inpainting
    # ------------------------------------------------------------------
    print("\n[Step 4/5] AI Occlusion Inpainting")
    try:
        run_ai_occlusion_inpainting()
    except Exception as e:
        print(f"  [WARNING] Inpainting step failed (non-fatal): {e}")

    # ------------------------------------------------------------------
    # Step 5: Generate web viewer HTML
    # ------------------------------------------------------------------
    print("\n[Step 5/5] Generating WebGL 3D Viewer")
    try:
        # Import here to avoid circular dependency at module level
        sys.path.insert(0, _src_dir)
        from generate_web_viewer import generate_web_viewer
        generate_web_viewer()
        print("  Web viewer generated at: data/colmap_output/view_3d_model.html")
    except Exception as e:
        print(f"  [WARNING] Web viewer generation failed: {e}")

    print("\n" + "=" * 70)
    print("[SUCCESS] Full 3D Reconstruction Pipeline Finished!")
    print(f"  Open data/colmap_output/view_3d_model.html in a browser to view the result.")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Run AeroTwin-3D drone video-to-3D reconstruction pipeline. "
                    "All quality parameters are read from config.yaml."
    )
    parser.add_argument(
        "--video", type=str, default=None,
        help="Input drone video path (default: data/raw_video/uploaded_video.mp4)"
    )
    parser.add_argument(
        "--srt", type=str, default=None,
        help="Input drone telemetry SRT path (default: data/raw_video/uploaded_video.srt)"
    )
    args = parser.parse_args()
    run_full_pipeline(video_path=args.video, srt_path=args.srt)


if __name__ == "__main__":
    main()

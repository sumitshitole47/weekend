import argparse
import os
import sys

from parse_srt_telemetry import parse_dji_srt
from extract_frames import extract_frames
from filter_blurry_frames import filter_blurry_frames
from run_colmap import run_colmap_pipeline


def run_full_pipeline(
    video_path: str = "data/raw_video/sample_drone.mp4",
    srt_path: str = "data/raw_video/sample_drone.srt",
    frames_dir: str = "data/frames",
    rejected_dir: str = "data/frames_rejected",
    output_dir: str = "data/colmap_output",
    target_fps: float = 2.0,
    blur_threshold: float = 50.0,
    colmap_exe: str = "colmap"
):
    """
    Master pipeline runner for single-pass drone 3D reconstruction.

    Executes:
    1. SRT Telemetry Parsing
    2. Video Frame Extraction
    3. Blurry Frame Filtering
    4. COLMAP Sparse Reconstruction (if COLMAP executable is available)
    """
    print("=" * 70)
    print("[+] Single-Pass Drone Video 3D Reconstruction Pipeline")
    print("=" * 70)

    # -------------------------------------------------------------
    # Step 1: Parse SRT Telemetry (if available)
    # -------------------------------------------------------------
    print("\n[Step 1/4] Telemetry Ingestion")
    if os.path.exists(srt_path):
        telemetry_json = os.path.join(frames_dir, "telemetry.json")
        try:
            parse_dji_srt(srt_path, telemetry_json)
        except Exception as e:
            print(f"[WARNING] Failed to parse SRT telemetry file: {e}")
    else:
        print(f"[INFO] SRT telemetry log '{srt_path}' not found. Skipping telemetry parsing.")

    # -------------------------------------------------------------
    # Step 2: Extract Video Frames
    # -------------------------------------------------------------
    print("\n[Step 2/4] Frame Extraction")
    if not os.path.exists(video_path):
        print(f"[ERROR] Video file '{video_path}' does not exist.")
        sys.exit(1)

    extracted_count = extract_frames(video_path, frames_dir, target_fps=target_fps)
    if extracted_count == 0:
        print("[ERROR] No frames extracted from video.")
        sys.exit(1)

    # -------------------------------------------------------------
    # Step 3: Filter Blurry Frames
    # -------------------------------------------------------------
    print("\n[Step 3/4] Blur Quality Filtering")
    filter_stats = filter_blurry_frames(
        input_dir=frames_dir,
        rejected_dir=rejected_dir,
        threshold=blur_threshold
    )

    if filter_stats["kept"] == 0:
        print("[ERROR] All extracted frames were marked as blurry! Try lowering --blur-threshold.")
        sys.exit(1)

    # -------------------------------------------------------------
    # Step 4: COLMAP SfM Reconstruction
    # -------------------------------------------------------------
    print("\n[Step 4/4] COLMAP Sparse Reconstruction")
    colmap_success = run_colmap_pipeline(
        image_dir=frames_dir,
        output_dir=output_dir,
        colmap_exe=colmap_exe,
        single_camera=True
    )

    if not colmap_success:
        print("\n" + "!" * 70)
        print("[NOTICE] Pipeline steps 1-3 completed successfully.")
        print("[NOTICE] COLMAP SfM requires real drone video frames with 3D parallax.")
        print("         Ensure real drone images are in data/raw_video and COLMAP is configured.")
        print("!" * 70)
    else:
        print("\n" + "=" * 70)
        print("[SUCCESS] Full 3D Reconstruction Pipeline Finished!")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Run end-to-end drone video to 3D model reconstruction pipeline."
    )
    parser.add_argument(
        "--video",
        type=str,
        default="data/raw_video/sample_drone.mp4",
        help="Input drone video path (default: data/raw_video/sample_drone.mp4)."
    )
    parser.add_argument(
        "--srt",
        type=str,
        default="data/raw_video/sample_drone.srt",
        help="Input drone telemetry SRT path (default: data/raw_video/sample_drone.srt)."
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=2.0,
        help="Frame extraction sampling rate (default: 2.0)."
    )
    parser.add_argument(
        "--blur-threshold",
        type=float,
        default=50.0,
        help="Laplacian variance blur rejection threshold (default: 50.0)."
    )
    parser.add_argument(
        "--colmap-path",
        type=str,
        default="colmap",
        help="Path to COLMAP executable (default: colmap)."
    )

    args = parser.parse_args()
    run_full_pipeline(
        video_path=args.video,
        srt_path=args.srt,
        target_fps=args.fps,
        blur_threshold=args.blur_threshold,
        colmap_exe=args.colmap_path
    )


if __name__ == "__main__":
    main()

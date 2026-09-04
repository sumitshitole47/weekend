from pipeline.dynamic_reconstructor import reconstruct_dense_point_cloud_from_frames
from pipeline.preprocessor import preprocess_drone_video
from pipeline.telemetry import parse_srt_telemetry_file
import os

def test_fresh_reconstruction():
    print("[TEST] Running 3D vision reconstruction on uploaded video files...")
    video_path = "data/raw_video/drone_clip.mp4"
    srt_path = "data/raw_video/drone_clip.srt"

    num_frames = preprocess_drone_video(video_path)
    print(f"Extracted {num_frames} keyframes.")

    records, disp, scale = parse_srt_telemetry_file(srt_path)
    print(f"Parsed {len(records)} telemetry records.")

    metrics = reconstruct_dense_point_cloud_from_frames()
    print(f"[RECONSTRUCTION TEST RESULT]: {metrics}")

if __name__ == "__main__":
    test_fresh_reconstruction()

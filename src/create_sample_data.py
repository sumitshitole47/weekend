import os
import cv2
import numpy as np


def create_synthetic_drone_dataset(
    output_video_path: str = "data/raw_video/sample_drone.mp4",
    output_srt_path: str = "data/raw_video/sample_drone.srt",
    duration_sec: int = 10,
    fps: int = 30
):
    """
    Generate a synthetic drone flyover video and matching SRT subtitle telemetry file
    for testing the 3D reconstruction pipeline.
    """
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    os.makedirs(os.path.dirname(output_srt_path), exist_ok=True)

    width, height = 640, 480
    total_frames = duration_sec * fps

    # Define video codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    print(f"[+] Generating synthetic drone video ({duration_sec}s, {total_frames} frames)...")

    base_lat = 28.613939
    base_lon = 77.209021
    base_alt = 50.0

    srt_entries = []

    for f_idx in range(total_frames):
        # Create a synthetic aerial landscape pattern with panning motion
        offset_x = int(f_idx * 2.5)
        offset_y = int(f_idx * 1.2)

        # Background terrain texture simulation
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:, :] = (34, 139, 34)  # Forest green ground

        # Draw grid lines to simulate agricultural fields / terrain features
        for x in range((offset_x % 80), width, 80):
            cv2.line(img, (x, 0), (x, height), (50, 160, 50), 2)
        for y in range((offset_y % 80), height, 80):
            cv2.line(img, (0, y), (width, y), (50, 160, 50), 2)

        # Draw ground features / structures
        rect_x = (200 - offset_x) % width
        rect_y = (150 - offset_y) % height
        cv2.rectangle(img, (rect_x, rect_y), (rect_x + 100, rect_y + 80), (128, 128, 128), -1)
        cv2.putText(img, "Building A", (rect_x + 10, rect_y + 45), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        circle_x = (450 - offset_x) % width
        circle_y = (300 - offset_y) % height
        cv2.circle(img, (circle_x, circle_y), 40, (0, 0, 255), -1)

        out.write(img)

        # Generate matching telemetry entry every second (every `fps` frames)
        if f_idx % fps == 0:
            sec_idx = f_idx // fps
            start_tc = f"00:00:{sec_idx:02d},000"
            end_tc = f"00:00:{sec_idx+1:02d},000"
            cur_lat = base_lat + (sec_idx * 0.00001)
            cur_lon = base_lon + (sec_idx * 0.000015)
            cur_alt = base_alt + (sec_idx * 0.2)

            srt_entry = (
                f"{sec_idx + 1}\n"
                f"{start_tc} --> {end_tc}\n"
                f"[latitude: {cur_lat:.6f}] [longitude: {cur_lon:.6f}] [abs_alt: {cur_alt:.1f}] [gimbal_pitch: -45.0]\n"
            )
            srt_entries.append(srt_entry)

    out.release()
    print(f"[SUCCESS] Video saved to: '{output_video_path}'")

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries))

    print(f"[SUCCESS] Telemetry SRT saved to: '{output_srt_path}'")


if __name__ == "__main__":
    create_synthetic_drone_dataset()

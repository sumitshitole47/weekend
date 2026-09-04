import os
import cv2
import numpy as np


def extract_frames(video_path: str, output_dir: str, sample_rate: int = 10, min_sharpness: float = 50.0):
    """
    Extract frames from a drone video file at a given sampling interval,
    filtering out overly blurry frames.

    :param video_path: Path to raw drone input video.
    :param output_dir: Directory where extracted frame images will be saved.
    :param sample_rate: Save 1 frame out of every `sample_rate` frames.
    :param min_sharpness: Threshold for Laplacian variance image sharpness check.
    :return: Number of valid frames extracted.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)

    frame_count = 0
    saved_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % sample_rate == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

            if sharpness >= min_sharpness:
                frame_filename = os.path.join(output_dir, f"frame_{saved_count:05d}.jpg")
                cv2.imwrite(frame_filename, frame)
                saved_count += 1

        frame_count += 1

    cap.release()
    print(f"Extracted {saved_count} sharp frames from {frame_count} total video frames.")
    return saved_count


if __name__ == "__main__":
    import sys
    print("Frame Extraction module ready.")

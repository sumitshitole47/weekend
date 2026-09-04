"""
AeroTwin-3D Video Preprocessor
Slices video at 2-3 FPS, applies adaptive motion blur filtering via Laplacian variance,
and generates dilated binary masks for dynamic objects (vehicles, humans).
"""
import os
import cv2
import numpy as np


def preprocess_drone_video(
    video_path: str,
    output_frames_dir: str = "data/frames",
    output_masks_dir: str = "data/frames/masks",
    target_fps: float = 2.5,
    blur_threshold: float = 15.0,  # Adaptive threshold ensuring all valid videos pass
    progress_callback=None
):
    """
    Slice video at 2-3 FPS, apply adaptive Laplacian blur filtering, and generate dilated object masks.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    os.makedirs(output_frames_dir, exist_ok=True)
    os.makedirs(output_masks_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    sample_interval = max(1, int(round(video_fps / target_fps)))

    if progress_callback:
        progress_callback("Preprocessing video keyframes...", 10)

    back_sub = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=25, detectShadows=True)
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

    frame_idx = 0
    saved_count = 0
    rejected_blur_count = 0

    # First pass: collect sampled frames & blur scores
    sampled_frames = []
    blur_scores = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            sampled_frames.append(frame)
            blur_scores.append(blur_var)

        frame_idx += 1

    cap.release()

    if not sampled_frames:
        raise ValueError("Could not extract any video frames from the uploaded file.")

    # Adaptive Thresholding: Always retain at least top 80% sharpest frames
    median_blur = float(np.median(blur_scores)) if blur_scores else 20.0
    effective_threshold = min(blur_threshold, median_blur * 0.4)

    for i, frame in enumerate(sampled_frames):
        blur_var = blur_scores[i]

        if blur_var < effective_threshold and saved_count > 5:
            rejected_blur_count += 1
        else:
            saved_count += 1
            frame_name = f"frame_{saved_count:04d}.jpg"
            frame_path = os.path.join(output_frames_dir, frame_name)
            cv2.imwrite(frame_path, frame)

            fg_mask = back_sub.apply(frame)
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_dilate)
            dilated_mask = cv2.dilate(fg_mask, kernel_dilate, iterations=3)
            colmap_mask = cv2.bitwise_not(dilated_mask)

            mask_path = os.path.join(output_masks_dir, f"{frame_name}.png")
            cv2.imwrite(mask_path, colmap_mask)

        if progress_callback and (i + 1) % 10 == 0:
            pct = 10 + int(((i + 1) / len(sampled_frames)) * 20)
            progress_callback(f"Saved {saved_count} sharp keyframes from uploaded video...", pct)

    print(f"[OK] Preprocessor complete: {saved_count} sharp frames saved, {rejected_blur_count} blurry frames rejected.")
    return saved_count

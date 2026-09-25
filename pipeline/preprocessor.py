"""
AeroTwin-3D Video Preprocessor
Slices video at 2.5 FPS, applies adaptive motion blur filtering via Laplacian variance,
and generates dilated binary masks for dynamic objects (vehicles, humans).
"""
import os
import glob
import cv2
import numpy as np
from pipeline.config import load_config


def preprocess_drone_video(
    video_path: str,
    output_frames_dir: str = None,
    output_masks_dir: str = None,
    target_fps: float = None,
    blur_threshold: float = None,
    progress_callback=None
):
    """
    Slice video at target FPS (default 2.5), apply adaptive Laplacian blur filtering, and generate dilated object masks.
    """
    cfg = load_config()
    fe_cfg = cfg.get("frame_extraction", {})
    paths_cfg = cfg.get("output_paths", {})

    output_frames_dir = output_frames_dir or paths_cfg.get("frames_dir", "data/frames")
    output_masks_dir = output_masks_dir or paths_cfg.get("masks_dir", "data/frames/masks")
    target_fps = target_fps or fe_cfg.get("target_fps", 2.5)
    blur_threshold = blur_threshold or fe_cfg.get("blur_threshold", 15.0)

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Clean stale keyframes and masks from previous video uploads
    if os.path.exists(output_frames_dir):
        for f in glob.glob(os.path.join(output_frames_dir, "*.jpg")) + glob.glob(os.path.join(output_frames_dir, "*.png")):
            try:
                os.remove(f)
            except Exception:
                pass
    if os.path.exists(output_masks_dir):
        for f in glob.glob(os.path.join(output_masks_dir, "*.jpg")) + glob.glob(os.path.join(output_masks_dir, "*.png")):
            try:
                os.remove(f)
            except Exception:
                pass

    os.makedirs(output_frames_dir, exist_ok=True)
    os.makedirs(output_masks_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Unable to open video file: '{video_path}'. Ensure it is a valid MP4/AVI video format.")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    duration_sec = total_frames / max(1.0, video_fps)

    # Adaptive Target FPS: ensure 25-50 high-overlap keyframes regardless of video duration
    if duration_sec < 10.0:
        eff_fps = max(3.0, min(5.0, 30.0 / duration_sec))
    elif duration_sec < 30.0:
        eff_fps = target_fps or 2.5
    else:
        eff_fps = max(1.0, 45.0 / duration_sec)

    sample_interval = max(1, int(round(video_fps / eff_fps)))
    print(f"[PREPROCESSOR] Video Duration: {duration_sec:.1f}s ({total_frames} frames @ {video_fps:.1f} FPS) -> Sampling at {eff_fps:.1f} FPS (every {sample_interval} frames)")

    if progress_callback:
        progress_callback("Preprocessing video keyframes...", 10)

    frame_idx = 0
    saved_count = 0
    rejected_blur_count = 0

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

    # Adaptive Thresholding: Always retain top sharpest frames
    median_blur = float(np.median(blur_scores)) if blur_scores else 20.0
    effective_threshold = min(blur_threshold, median_blur * 0.35)

    for i, frame in enumerate(sampled_frames):
        blur_var = blur_scores[i]

        if blur_var < effective_threshold and saved_count > 10:
            rejected_blur_count += 1
        else:
            saved_count += 1
            frame_name = f"frame_{saved_count:04d}.jpg"
            frame_path = os.path.join(output_frames_dir, frame_name)
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 98])

    # Track video dimensions & resolution label
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap else 1920
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if cap else 1080
    res_label = f"{width}x{height}"
    if width >= 3840 or height >= 2160:
        res_label += " (4K UHD)"
    elif width >= 1920 or height >= 1080:
        res_label += " (FHD)"
    elif width >= 1280 or height >= 720:
        res_label += " (HD)"

    # Generate dynamic object suppression masks
    dynamic_masked_count = 0
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=10, varThreshold=25, detectShadows=False)
    saved_frames = sorted(glob.glob(os.path.join(output_frames_dir, "*.jpg")))

    for sf in saved_frames:
        img = cv2.imread(sf)
        if img is not None:
            fg = bg_subtractor.apply(img)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            fg_clean = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
            fg_clean = cv2.dilate(fg_clean, kernel, iterations=2)
            contours, _ = cv2.findContours(fg_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if sum(1 for c in contours if cv2.contourArea(c) > 200) > 0:
                dynamic_masked_count += 1
            mask_name = os.path.basename(sf).replace(".jpg", ".png")
            cv2.imwrite(os.path.join(output_masks_dir, mask_name), fg_clean)

    # Save video extraction metrics to building_metrics.json
    metrics_path = "data/colmap_output/building_metrics.json"
    os.makedirs(os.path.dirname(metrics_path), exist_ok=True)
    existing_metrics = {}
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                import json
                existing_metrics = json.load(f)
        except Exception:
            pass

    existing_metrics.update({
        "video_duration_s": round(duration_sec, 1),
        "video_resolution": res_label,
        "video_fps": round(video_fps, 1),
        "total_frames_detected": total_frames,
        "keyframes_selected": saved_count,
        "blurred_frames_rejected": rejected_blur_count,
        "dynamic_objects_masked": dynamic_masked_count,
    })

    try:
        with open(metrics_path, "w", encoding="utf-8") as f:
            import json
            json.dump(existing_metrics, f, indent=2)
    except Exception as me:
        print(f"[WARNING] Could not update metrics with video stats: {me}")

    print(f"[OK] Preprocessor complete: {saved_count} sharp frames saved, {rejected_blur_count} blurry frames rejected, {dynamic_masked_count} dynamic masks generated.")
    return saved_count


import os
import re
import cv2
from fastapi import HTTPException, UploadFile


ALLOWED_VIDEO_EXTENSIONS = {".mp4"}
ALLOWED_TELEMETRY_EXTENSIONS = {".srt"}


def validate_video_file(file: UploadFile) -> str:
    """Validate that uploaded video is strictly .mp4 format."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video format '{ext}'. Only '.mp4' files are accepted."
        )
    return ext


def validate_telemetry_file(file: UploadFile) -> str:
    """Validate that uploaded telemetry is strictly .srt format."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_TELEMETRY_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid telemetry format '{ext}'. Only '.srt' files are accepted."
        )
    return ext


def get_video_duration_seconds(video_path: str) -> float:
    """Extract actual video duration in seconds using OpenCV."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Unable to read video file. Invalid or corrupt MP4 container.")
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    
    if frame_count <= 0 or fps <= 0:
        return 0.0
    return float(frame_count / fps)


def parse_srt_duration_seconds(srt_path: str) -> float:
    """Parse timestamp range (first start time to last end time) from .srt file."""
    if not os.path.exists(srt_path):
        return 0.0

    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Pattern for 00:00:01,000 --> 00:00:02,000 or 00:00:01.000 --> 00:00:02.000
    pattern = r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
    matches = re.findall(pattern, content)

    if not matches:
        return 0.0

    def timestamp_to_seconds(h, m, s, ms):
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    first_start = timestamp_to_seconds(*matches[0][:4])
    last_end = timestamp_to_seconds(*matches[-1][4:])

    duration = last_end - first_start
    return max(0.0, float(duration))


def validate_video_srt_alignment(video_path: str, srt_path: str):
    """
    Validates that the .srt file timestamp range overlaps with the video's actual duration.
    If they clearly do not correspond, raises an HTTP 400 error.
    """
    video_dur = get_video_duration_seconds(video_path)
    srt_dur = parse_srt_duration_seconds(srt_path)

    if video_dur <= 0 or srt_dur <= 0:
        return  # Cannot compare if duration unparseable

    # Allow up to 35% margin or 3.0s threshold
    allowed_diff = max(3.0, video_dur * 0.35)
    diff = abs(video_dur - srt_dur)

    if diff > allowed_diff:
        raise HTTPException(
            status_code=400,
            detail=f"Telemetry duration mismatch: .srt covers {srt_dur:.1f}s, but uploaded video is {video_dur:.1f}s. Please upload matching video and flight telemetry files."
        )

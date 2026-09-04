"""
AeroTwin-3D File Format Validators
Strict file format enforcement: Accepts ONLY .mp4 for drone video and .srt for telemetry.
"""
import os
from fastapi import HTTPException, UploadFile


ALLOWED_VIDEO_EXTENSIONS = {".mp4"}
ALLOWED_TELEMETRY_EXTENSIONS = {".srt"}


def validate_video_file(file: UploadFile) -> str:
    """
    Validate that uploaded video is strictly .mp4 format.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid video format '{ext}'. Only '.mp4' files are accepted."
        )
    return ext


def validate_telemetry_file(file: UploadFile) -> str:
    """
    Validate that uploaded telemetry is strictly .srt format.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_TELEMETRY_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid telemetry format '{ext}'. Only '.srt' files are accepted."
        )
    return ext

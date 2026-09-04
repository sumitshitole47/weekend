import argparse
import math
import os
import cv2


def extract_frames(video_path: str, output_dir: str, target_fps: float = 2.0) -> int:
    """
    Extract frames from a video file at a specified target frame rate using OpenCV.

    :param video_path: Path to input video file.
    :param output_dir: Path to directory where frame images will be saved.
    :param target_fps: Extraction rate in frames per second (default: 2.0).
    :return: Total number of frames extracted and saved.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Input video file not found: {video_path}")

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video file: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if video_fps <= 0:
        print("Warning: Could not read valid FPS from video header. Defaulting step interval to 1.")
        frame_interval = 1
    else:
        # Determine number of video frames to step between extracted frames
        frame_interval = max(1, math.floor(video_fps / target_fps))

    print(f"Input Video: {video_path}")
    print(f"Video FPS: {video_fps:.2f} | Total Frames: {total_video_frames}")
    print(f"Extracting at {target_fps} FPS (sampling 1 frame every {frame_interval} video frame(s))...")

    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % frame_interval == 0:
            saved_count += 1
            filename = os.path.join(output_dir, f"frame_{saved_count:04d}.jpg")
            cv2.imwrite(filename, frame)

        frame_count += 1

    cap.release()
    print(f"Frame extraction complete! Total frames extracted: {saved_count}")
    return saved_count


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from a video file at a specified frame rate using OpenCV."
    )
    parser.add_argument(
        "video_path",
        type=str,
        help="Path to the input video file (e.g. data/raw_video/drone.mp4)."
    )
    parser.add_argument(
        "output_dir",
        type=str,
        nargs="?",
        default="data/frames",
        help="Output directory to save extracted frame images (default: data/frames)."
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=2.0,
        help="Target frame extraction rate in frames per second (default: 2.0)."
    )

    args = parser.parse_args()
    extract_frames(args.video_path, args.output_dir, target_fps=args.fps)


if __name__ == "__main__":
    main()

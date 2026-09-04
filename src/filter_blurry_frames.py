import argparse
import os
import shutil
import cv2


def filter_blurry_frames(
    input_dir: str = "data/frames",
    rejected_dir: str = "data/frames_rejected",
    threshold: float = 100.0,
    extensions: tuple = (".jpg", ".jpeg", ".png")
):
    """
    Scan frame images in `input_dir`, compute OpenCV Laplacian variance (blur score),
    and move frames scoring below `threshold` into `rejected_dir`.

    :param input_dir: Directory containing input frame images.
    :param rejected_dir: Destination directory for blurry frames.
    :param threshold: Minimum sharpness score (Laplacian variance).
    :param extensions: File extensions to process.
    :return: Summary dictionary with metrics.
    """
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    # Discover frame files
    image_paths = [
        os.path.join(input_dir, fname)
        for fname in os.listdir(input_dir)
        if fname.lower().endswith(extensions)
    ]
    image_paths.sort()

    total_images = len(image_paths)
    if total_images == 0:
        print(f"No image files found in '{input_dir}'.")
        return {
            "total": 0,
            "kept": 0,
            "rejected": 0,
            "min_score": 0.0,
            "max_score": 0.0,
            "avg_score": 0.0,
        }

    os.makedirs(rejected_dir, exist_ok=True)

    kept_count = 0
    rejected_count = 0
    blur_scores = []

    print(f"Analyzing {total_images} frame(s) in '{input_dir}' with blur threshold = {threshold:.2f}...")

    for img_path in image_paths:
        img = cv2.imread(img_path)
        if img is None:
            print(f"Warning: Could not read '{img_path}', skipping.")
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        blur_scores.append(score)

        filename = os.path.basename(img_path)

        if score < threshold:
            rejected_count += 1
            dest_path = os.path.join(rejected_dir, filename)
            shutil.move(img_path, dest_path)
        else:
            kept_count += 1

    min_score = min(blur_scores) if blur_scores else 0.0
    max_score = max(blur_scores) if blur_scores else 0.0
    avg_score = sum(blur_scores) / len(blur_scores) if blur_scores else 0.0

    print("\n" + "=" * 50)
    print("=== Frame Blur Filtering Summary ===")
    print("=" * 50)
    print(f"Total Frames Scanned:  {total_images}")
    print(f"Frames Kept:           {kept_count}")
    print(f"Frames Rejected:       {rejected_count} (moved to '{rejected_dir}')")
    print(f"Blur Score Range:      [{min_score:.2f} ... {max_score:.2f}]")
    print(f"Average Blur Score:    {avg_score:.2f}")
    print("=" * 50)

    return {
        "total": total_images,
        "kept": kept_count,
        "rejected": rejected_count,
        "min_score": min_score,
        "max_score": max_score,
        "avg_score": avg_score,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scan frame images and move blurry frames (low Laplacian variance) to a rejected folder."
    )
    parser.add_argument(
        "input_dir",
        type=str,
        nargs="?",
        default="data/frames",
        help="Directory containing frame images to analyze (default: data/frames)."
    )
    parser.add_argument(
        "--rejected-dir",
        type=str,
        default="data/frames_rejected",
        help="Directory to move rejected blurry frames to (default: data/frames_rejected)."
    )
    parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=100.0,
        help="Laplacian variance threshold. Frames scoring below this threshold are moved (default: 100.0)."
    )

    args = parser.parse_args()
    filter_blurry_frames(args.input_dir, args.rejected_dir, threshold=args.threshold)


if __name__ == "__main__":
    main()

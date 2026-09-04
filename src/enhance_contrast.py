import argparse
import os
import cv2
import numpy as np


def enhance_frame_illumination(img: np.ndarray) -> np.ndarray:
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) in LAB color space
    to recover feature details in shadowed building facades and bright areas.
    """
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    # Apply CLAHE to L-channel
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l_channel)

    # Merge channels
    limg = cv2.merge((cl, a_channel, b_channel))
    enhanced_bgr = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    return enhanced_bgr


def process_directory_illumination(input_dir: str, output_dir: str = None):
    """
    Enhance lighting and contrast for all frame images in input_dir.
    """
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Directory not found: {input_dir}")

    if output_dir is None:
        output_dir = input_dir

    os.makedirs(output_dir, exist_ok=True)
    images = [f for f in os.listdir(input_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

    print(f"[+] Applying CLAHE illumination enhancement to {len(images)} frame(s)...")

    count = 0
    for fname in images:
        in_path = os.path.join(input_dir, fname)
        out_path = os.path.join(output_dir, fname)

        img = cv2.imread(in_path)
        if img is None:
            continue

        enhanced = enhance_frame_illumination(img)
        cv2.imwrite(out_path, enhanced)
        count += 1

    print(f"[SUCCESS] Enhanced illumination for {count} frame(s) in '{output_dir}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Apply CLAHE adaptive illumination enhancement to drone keyframes for shadow detail recovery."
    )
    parser.add_argument(
        "input_dir",
        type=str,
        nargs="?",
        default="data/frames",
        help="Directory containing frame images (default: data/frames)."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/frames",
        help="Output directory for enhanced images (default: overwrite in data/frames)."
    )

    args = parser.parse_args()
    process_directory_illumination(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()

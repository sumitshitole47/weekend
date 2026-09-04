import argparse
import os
import cv2
import numpy as np


def generate_motion_masks(input_dir: str, mask_output_dir: str):
    """
    Generate dynamic object masks for frame images using background subtraction
    and motion analysis. Prevents moving vehicles, people, and transient artifacts
    from corrupting 3D photogrammetry feature matching.
    """
    if not os.path.exists(input_dir):
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    os.makedirs(mask_output_dir, exist_ok=True)
    images = [f for f in os.listdir(input_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    images.sort()

    if len(images) == 0:
        print(f"[INFO] No images found in '{input_dir}' for mask generation.")
        return

    print(f"[+] Generating dynamic object motion masks for {len(images)} frame(s)...")

    # MOG2 Background Subtractor for dynamic motion detection
    back_sub = cv2.createBackgroundSubtractorMOG2(history=50, varThreshold=25, detectShadows=True)

    mask_count = 0

    for fname in images:
        img_path = os.path.join(input_dir, fname)
        img = cv2.imread(img_path)
        if img is None:
            continue

        # Apply background subtraction
        fg_mask = back_sub.apply(img)

        # Morphological operations to clean noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.dilate(fg_mask, kernel, iterations=2)

        # COLMAP masks: 255 = keep static background, 0 = mask out dynamic moving object
        colmap_mask = cv2.bitwise_not(fg_mask)

        # Save mask with COLMAP convention filename (e.g. frame_0001.jpg.png)
        mask_filename = f"{fname}.png"
        mask_path = os.path.join(mask_output_dir, mask_filename)
        cv2.imwrite(mask_path, colmap_mask)
        mask_count += 1

    print(f"[SUCCESS] Generated {mask_count} dynamic object masks in '{mask_output_dir}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Generate dynamic object feature masks (vehicles/humans) for COLMAP feature extractor."
    )
    parser.add_argument(
        "input_dir",
        type=str,
        nargs="?",
        default="data/frames",
        help="Directory containing frame images (default: data/frames)."
    )
    parser.add_argument(
        "--mask-dir",
        type=str,
        default="data/frames/masks",
        help="Output directory for image masks (default: data/frames/masks)."
    )

    args = parser.parse_args()
    generate_motion_masks(args.input_dir, args.mask_dir)


if __name__ == "__main__":
    main()

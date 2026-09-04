import argparse
import os
import struct
import numpy as np


def export_colmap_bin_to_ply(bin_path: str, output_ply_path: str):
    """
    Convert COLMAP points3D.bin binary point cloud to a standard ASCII PLY file.
    Can be opened directly in MeshLab, CloudCompare, Blender, or Windows 3D Viewer.
    """
    if not os.path.exists(bin_path):
        raise FileNotFoundError(f"Binary file not found: {bin_path}")

    points = []
    colors = []

    with open(bin_path, "rb") as f:
        num_points = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_points):
            binary_point_header = f.read(43)
            _, x, y, z, r, g, b, _ = struct.unpack("<QdddBBBd", binary_point_header)

            track_len = struct.unpack("<Q", f.read(8))[0]
            f.read(8 * track_len)

            points.append((x, y, z))
            colors.append((r, g, b))

    os.makedirs(os.path.dirname(output_ply_path), exist_ok=True)

    header = (
        "ply\n"
        "format ascii 1.0\n"
        "comment Exported from COLMAP points3D.bin\n"
        f"element vertex {len(points)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "end_header\n"
    )

    with open(output_ply_path, "w", encoding="utf-8") as f:
        f.write(header)
        for (x, y, z), (r, g, b) in zip(points, colors):
            f.write(f"{x:.6f} {y:.6f} {z:.6f} {r} {g} {b}\n")

    print(f"[SUCCESS] Exported {len(points):,} 3D points to PLY file: '{output_ply_path}'")


def main():
    parser = argparse.ArgumentParser(
        description="Convert COLMAP points3D.bin into standard ASCII PLY 3D point cloud file."
    )
    parser.add_argument(
        "input_bin",
        type=str,
        nargs="?",
        default="data/colmap_output/sparse/0/points3D.bin",
        help="Path to points3D.bin file (default: data/colmap_output/sparse/0/points3D.bin)."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/colmap_output/model_3d.ply",
        help="Output PLY file path (default: data/colmap_output/model_3d.ply)."
    )

    args = parser.parse_args()
    export_colmap_bin_to_ply(args.input_bin, args.output)


if __name__ == "__main__":
    main()

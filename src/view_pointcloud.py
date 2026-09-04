import argparse
import os
import struct
import sys
import numpy as np


def read_points3d_bin(bin_path: str):
    """
    Parse COLMAP points3D.bin binary file format into points and RGB colors.
    """
    points = []
    colors = []
    with open(bin_path, "rb") as f:
        num_points = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_points):
            # 8 (uint64 id) + 24 (3x double xyz) + 3 (3x uint8 rgb) + 8 (double error) = 43 bytes
            binary_point_header = f.read(43)
            _, x, y, z, r, g, b, _ = struct.unpack("<QdddBBBd", binary_point_header)

            # Read track length and skip track data
            track_len = struct.unpack("<Q", f.read(8))[0]
            f.read(8 * track_len)  # 4 bytes image_id + 4 bytes point2d_idx

            points.append([x, y, z])
            colors.append([r / 255.0, g / 255.0, b / 255.0])

    return np.array(points, dtype=np.float64), np.array(colors, dtype=np.float64)


def read_points3d_txt(txt_path: str):
    """
    Parse COLMAP points3D.txt text file format into points and RGB colors.
    """
    points = []
    colors = []
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 7:
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                r, g, b = int(parts[4]), int(parts[5]), int(parts[6])
                points.append([x, y, z])
                colors.append([r / 255.0, g / 255.0, b / 255.0])

    return np.array(points, dtype=np.float64), np.array(colors, dtype=np.float64)


def load_colmap_pointcloud(path: str):
    """
    Load a point cloud from COLMAP sparse output (points3D.bin, points3D.txt)
    or standard PLY/PCD files. Automatically searches directory if path is a folder.
    """
    target_file = path

    # If directory passed, resolve points3D file location
    if os.path.isdir(path):
        candidate_paths = [
            os.path.join(path, "points3D.bin"),
            os.path.join(path, "0", "points3D.bin"),
            os.path.join(path, "points3D.txt"),
            os.path.join(path, "0", "points3D.txt"),
            os.path.join(path, "fused.ply"),
            os.path.join(path, "sparse.ply"),
        ]
        found = False
        for cand in candidate_paths:
            if os.path.isfile(cand):
                target_file = cand
                found = True
                break
        if not found:
            raise FileNotFoundError(
                f"Could not locate points3D.bin, points3D.txt, or .ply in folder: '{path}'"
            )

    print(f"[+] Loading COLMAP point cloud file: '{target_file}'")

    if target_file.endswith(".bin"):
        points, colors = read_points3d_bin(target_file)
    elif target_file.endswith(".txt"):
        points, colors = read_points3d_txt(target_file)
    else:
        try:
            import open3d as o3d
            pcd = o3d.io.read_point_cloud(target_file)
            points = np.asarray(pcd.points)
            colors = np.asarray(pcd.colors)
        except ImportError:
            raise ImportError("Open3D is required to load generic .ply/.pcd files.")

    num_points = len(points)
    print(f"[OK] Successfully loaded {num_points:,} 3D points.")

    if num_points > 0:
        min_b = points.min(axis=0)
        max_b = points.max(axis=0)
        print(f"   Bounding Box Extent: Min [{min_b[0]:.2f}, {min_b[1]:.2f}, {min_b[2]:.2f}] | Max [{max_b[0]:.2f}, {max_b[1]:.2f}, {max_b[2]:.2f}]")

    try:
        import open3d as o3d
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        pcd.colors = o3d.utility.Vector3dVector(colors)
        return pcd
    except ImportError:
        return {"points": points, "colors": colors}


def visualize_pointcloud(pcd, title: str = "COLMAP 3D Point Cloud Viewer"):
    """
    Open an interactive Open3D window to view and rotate the 3D point cloud.
    """
    try:
        import open3d as o3d
    except ImportError:
        print("[NOTICE] Open3D Python library is not installed in Python 3.14 environment.")
        print("         You can inspect the generated points3D.bin using COLMAP GUI (`colmap gui`).")
        return

    if isinstance(pcd, dict):
        o3d_pcd = o3d.geometry.PointCloud()
        o3d_pcd.points = o3d.utility.Vector3dVector(pcd["points"])
        o3d_pcd.colors = o3d.utility.Vector3dVector(pcd["colors"])
        pcd = o3d_pcd

    if len(pcd.points) == 0:
        print("[WARNING] Point cloud is empty. Viewer will not open.")
        return

    print("\n[+] Opening Open3D interactive viewer window...")
    print("   [Controls: Mouse Left-Click + Drag = Rotate | Mouse Wheel = Zoom | Shift + Left-Click = Pan]")

    o3d.visualization.draw_geometries(
        [pcd],
        window_name=title,
        width=1280,
        height=720,
        point_show_normal=False
    )


def main():
    parser = argparse.ArgumentParser(
        description="Load and interactively view COLMAP 3D point cloud (points3D.bin / points3D.txt / .ply)."
    )
    parser.add_argument(
        "input_path",
        type=str,
        nargs="?",
        default="data/colmap_output/sparse",
        help="Path to points3D.bin, points3D.txt, PLY file, or directory containing COLMAP output (default: data/colmap_output/sparse)."
    )

    args = parser.parse_args()

    try:
        pcd = load_colmap_pointcloud(args.input_path)
        visualize_pointcloud(pcd, title=f"3D Point Cloud Viewer - {os.path.basename(args.input_path)}")
    except Exception as e:
        print(f"[ERROR] Loading 3D point cloud: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

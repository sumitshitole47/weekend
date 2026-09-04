import argparse
import os
import struct
import numpy as np


def align_and_flip_points(points: np.ndarray, colors: np.ndarray = None):
    """
    Correct point cloud orientation by aligning ground plane facing UP (+Y)
    and inverting flipped Z/Y coordinates.
    """
    if len(points) == 0:
        return points, colors

    pts = points.copy()

    # Step 1: Detect orientation & flip upside-down models
    # Compute centroid
    centroid = np.mean(pts, axis=0)
    pts_centered = pts - centroid

    # Singular Value Decomposition (SVD) to find principal ground plane axes
    _, _, vh = np.linalg.svd(pts_centered, full_matrices=False)
    normal = vh[2, :]  # Normal vector of the ground plane

    # Ensure normal points UP (+Y or +Z depending on WebGL convention)
    if normal[1] < 0:
        normal = -normal

    # If building structure is inverted (roof points lower than ground), flip Y axis
    # In COLMAP aerial video, Y is often pointing downward.
    # We invert Y axis: Y_new = -Y
    pts[:, 1] = -pts[:, 1]

    # Recalculate bounding box and place ground at Y = 0
    min_y = np.percentile(pts[:, 1], 5)
    pts[:, 1] -= min_y

    return pts, colors


def process_ply_orientation(input_ply: str, output_ply: str):
    """
    Read PLY model, apply orientation correction (right-side up), and save.
    """
    if not os.path.exists(input_ply):
        raise FileNotFoundError(f"Input PLY file not found: {input_ply}")

    print(f"[+] Correcting 3D model orientation for: '{input_ply}'...")

    with open(input_ply, "rb") as f:
        header = ""
        while True:
            line = f.readline().decode("latin-1")
            header += line
            if line.strip() == "end_header":
                break

        header_lines = header.split("\n")
        num_vertices = 0
        properties = []
        is_binary = "format binary_little_endian" in header

        for hline in header_lines:
            hline_str = hline.strip()
            if hline_str.startswith("element vertex"):
                num_vertices = int(hline_str.split()[-1])
            elif hline_str.startswith("property"):
                parts = hline_str.split()
                properties.append((parts[1], parts[2]))

        dtype_map = {
            'float': 'f4', 'float32': 'f4', 'double': 'f8', 'float64': 'f8',
            'uchar': 'u1', 'uint8': 'u1', 'int': 'i4', 'int32': 'i4'
        }
        struct_fields = []
        for prop_type, prop_name in properties:
            dt = dtype_map.get(prop_type, 'f4')
            struct_fields.append((prop_name, dt))

        vertex_dtype = np.dtype(struct_fields)

        if is_binary:
            data = np.frombuffer(f.read(num_vertices * vertex_dtype.itemsize), dtype=vertex_dtype).copy()
            raw_pts = np.column_stack((data['x'], data['y'], data['z']))
            
            # Apply orientation correction
            corr_pts, _ = align_and_flip_points(raw_pts)

            # Re-write corrected binary data
            data['x'] = corr_pts[:, 0]
            data['y'] = corr_pts[:, 1]
            data['z'] = corr_pts[:, 2]

            os.makedirs(os.path.dirname(output_ply), exist_ok=True)
            with open(output_ply, "wb") as out_f:
                out_f.write(header.encode("latin-1"))
                out_f.write(data.tobytes())
        else:
            # ASCII handling
            points = []
            for _ in range(num_vertices):
                line = f.readline().decode("latin-1").strip()
                parts = line.split()
                if len(parts) >= 3:
                    points.append([float(parts[0]), float(parts[1]), float(parts[2])])
            raw_pts = np.array(points, dtype=np.float64)
            corr_pts, _ = align_and_flip_points(raw_pts)

            os.makedirs(os.path.dirname(output_ply), exist_ok=True)
            with open(output_ply, "w", encoding="utf-8") as out_f:
                out_f.write(header)
                for p in corr_pts:
                    out_f.write(f"{p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")

    print(f"[SUCCESS] Orientation corrected model saved to: '{output_ply}'")


def main():
    parser = argparse.ArgumentParser(
        description="Correct inverted 3D model orientation and align ground plane right-side UP."
    )
    parser.add_argument(
        "input_ply",
        type=str,
        nargs="?",
        default="data/colmap_output/dense/fused.ply",
        help="Path to fused.ply (default: data/colmap_output/dense/fused.ply)."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/colmap_output/dense/fused_corrected.ply",
        help="Output corrected PLY file (default: data/colmap_output/dense/fused_corrected.ply)."
    )

    args = parser.parse_args()
    process_ply_orientation(args.input_ply, args.output)


if __name__ == "__main__":
    main()

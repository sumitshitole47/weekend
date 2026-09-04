import argparse
import os
import struct
import numpy as np


def read_points_and_colors_from_ply(ply_path: str):
    with open(ply_path, "rb") as f:
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
            data = np.frombuffer(f.read(num_vertices * vertex_dtype.itemsize), dtype=vertex_dtype)
            points = np.column_stack((data['x'], data['y'], data['z']))
            if 'red' in data.dtype.names:
                colors = np.column_stack((data['red'], data['green'], data['blue']))
            else:
                colors = np.ones((num_vertices, 3), dtype=np.uint8) * 180
            return points, colors, header
        else:
            points = []
            colors = []
            for _ in range(num_vertices):
                line = f.readline().decode("latin-1").strip()
                parts = line.split()
                if len(parts) >= 6:
                    points.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    colors.append([int(parts[3]), int(parts[4]), int(parts[5])])
            return np.array(points), np.array(colors), header


def perform_3d_semantic_segmentation(points: np.ndarray, colors: np.ndarray):
    """
    Classify 3D points into:
    - Class 1: Buildings & Structures (Red: 239, 68, 68)
    - Class 2: Ground & Roads (Gray: 148, 163, 184)
    - Class 3: Vegetation & Trees (Green: 34, 197, 94)
    """
    if len(points) == 0:
        return colors

    z_vals = points[:, 1]  # Y axis in webgl / height
    min_z = np.percentile(z_vals, 5)
    max_z = np.percentile(z_vals, 95)
    h_above_ground = z_vals - min_z

    classified_colors = np.zeros_like(colors)

    for i in range(len(points)):
        hag = h_above_ground[i]
        r, g, b = colors[i]

        # Excess Green Index for Vegetation (ExG = 2G - R - B)
        exg = 2.0 * float(g) - float(r) - float(b)

        if hag > 3.0:
            if exg > 25.0:
                # 🌳 Vegetation (Green)
                classified_colors[i] = [34, 197, 94]
            else:
                # 🏢 Building Structure (Red)
                classified_colors[i] = [239, 68, 68]
        else:
            # 🛣️ Ground & Roads (Slate Gray)
            classified_colors[i] = [148, 163, 184]

    return classified_colors


def segment_ply_file(input_ply: str, output_ply: str):
    if not os.path.exists(input_ply):
        raise FileNotFoundError(f"Input PLY not found: {input_ply}")

    print(f"[+] Performing 3D Semantic Segmentation on: '{input_ply}'...")
    points, orig_colors, header = read_points_and_colors_from_ply(input_ply)
    classified_colors = perform_3d_semantic_segmentation(points, orig_colors)

    os.makedirs(os.path.dirname(output_ply), exist_ok=True)

    header_out = (
        "ply\n"
        "format ascii 1.0\n"
        "comment Classified 3D Semantic Segmentation (SIH26158)\n"
        f"element vertex {len(points)}\n"
        "property float x\n"
        "property float y\n"
        "property float z\n"
        "property uchar red\n"
        "property uchar green\n"
        "property uchar blue\n"
        "end_header\n"
    )

    with open(output_ply, "w", encoding="utf-8") as f:
        f.write(header_out)
        for i in range(len(points)):
            p = points[i]
            c = classified_colors[i]
            f.write(f"{p[0]:.4f} {p[1]:.4f} {p[2]:.4f} {c[0]} {c[1]} {c[2]}\n")

    print(f"[SUCCESS] Classified 3D Semantic Segmented PLY saved to: '{output_ply}'")


def main():
    parser = argparse.ArgumentParser(
        description="Perform multi-class 3D point cloud semantic segmentation (Buildings, Roads, Vegetation)."
    )
    parser.add_argument(
        "input_ply",
        type=str,
        nargs="?",
        default="data/colmap_output/dense/fused_corrected.ply",
        help="Path to fused_corrected.ply (default: data/colmap_output/dense/fused_corrected.ply)."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/colmap_output/dense/semantic_segmented.ply",
        help="Output semantic PLY file (default: data/colmap_output/dense/semantic_segmented.ply)."
    )

    args = parser.parse_args()
    segment_ply_file(args.input_ply, args.output)


if __name__ == "__main__":
    main()

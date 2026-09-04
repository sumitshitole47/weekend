import argparse
import json
import os
import struct
import numpy as np


def compute_building_height_metrics(points: np.ndarray) -> dict:
    """
    Compute ground elevation, peak structure height, and bounding box dimensions
    from 3D point cloud coordinates.
    """
    if len(points) == 0:
        return {
            "total_points": 0,
            "ground_elevation": 0.0,
            "peak_elevation": 0.0,
            "max_absolute_z": 0.0,
            "estimated_building_height": 0.0,
            "spatial_width_x": 0.0,
            "spatial_length_y": 0.0,
            "unit": "meters"
        }

    z_vals = points[:, 2]
    x_vals = points[:, 0]
    y_vals = points[:, 1]

    # Ground estimation (10th percentile)
    z_ground = float(np.percentile(z_vals, 10))
    # Peak elevation (98th percentile)
    z_peak = float(np.percentile(z_vals, 98))
    z_max_absolute = float(np.max(z_vals))

    building_height = max(0.0, z_peak - z_ground)

    x_extent = float(np.max(x_vals) - np.min(x_vals))
    y_extent = float(np.max(y_vals) - np.min(y_vals))

    return {
        "total_points": len(points),
        "ground_elevation": round(z_ground, 3),
        "peak_elevation": round(z_peak, 3),
        "max_absolute_z": round(z_max_absolute, 3),
        "estimated_building_height": round(building_height, 3),
        "spatial_width_x": round(x_extent, 3),
        "spatial_length_y": round(y_extent, 3),
        "unit": "meters"
    }


def read_points_from_bin(bin_path: str) -> np.ndarray:
    points = []
    with open(bin_path, "rb") as f:
        num_points = struct.unpack("<Q", f.read(8))[0]
        for _ in range(num_points):
            binary_point_header = f.read(43)
            _, x, y, z, _, _, _, _ = struct.unpack("<QdddBBBd", binary_point_header)

            track_len = struct.unpack("<Q", f.read(8))[0]
            f.read(8 * track_len)
            points.append([x, y, z])

    return np.array(points, dtype=np.float64)


def read_points_from_ply(ply_path: str) -> np.ndarray:
    """
    Parse ASCII or binary PLY files (e.g., COLMAP fused.ply).
    """
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

        if is_binary:
            # Build struct format per vertex
            dtype_map = {
                'float': 'f4', 'float32': 'f4', 'double': 'f8', 'float64': 'f8',
                'uchar': 'u1', 'uint8': 'u1', 'int': 'i4', 'int32': 'i4'
            }
            struct_fields = []
            for prop_type, prop_name in properties:
                dt = dtype_map.get(prop_type, 'f4')
                struct_fields.append((prop_name, dt))

            vertex_dtype = np.dtype(struct_fields)
            data = np.frombuffer(f.read(num_vertices * vertex_dtype.itemsize), dtype=vertex_dtype)
            return np.column_stack((data['x'], data['y'], data['z']))
        else:
            # ASCII parsing
            points = []
            for _ in range(num_vertices):
                line = f.readline().decode("latin-1").strip()
                parts = line.split()
                if len(parts) >= 3:
                    points.append([float(parts[0]), float(parts[1]), float(parts[2])])
            return np.array(points, dtype=np.float64)


def measure_model_height(input_path: str, output_json_path: str = "data/colmap_output/building_metrics.json"):
    """
    Load point cloud file and output building height and spatial dimension analysis.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print(f"[+] Analyzing structure elevation metrics from: '{input_path}'")

    if input_path.endswith(".bin"):
        points = read_points_from_bin(input_path)
    elif input_path.endswith(".ply"):
        points = read_points_from_ply(input_path)
    else:
        raise ValueError(f"Unsupported file format: {input_path}")

    metrics = compute_building_height_metrics(points)

    print("\n" + "=" * 55)
    print("=== Building Height & 3D Spatial Metrics ===")
    print("=" * 55)
    print(f"Total 3D Points Evaluated:  {metrics['total_points']:,}")
    print(f"Estimated Ground Elevation: {metrics['ground_elevation']} m")
    print(f"Building Peak Elevation:   {metrics['peak_elevation']} m")
    print(f"Calculated Structure Height:{metrics['estimated_building_height']} meters")
    print(f"Building Footprint Extent:  {metrics['spatial_width_x']}m x {metrics['spatial_length_y']}m")
    print("=" * 55)

    os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"[SAVED] Metrics exported to '{output_json_path}'.")
    return metrics


def main():
    parser = argparse.ArgumentParser(
        description="Compute building height and ground elevation metrics from 3D point cloud."
    )
    parser.add_argument(
        "input_path",
        type=str,
        nargs="?",
        default="data/colmap_output/sparse/0/points3D.bin",
        help="Path to points3D.bin or PLY file (default: data/colmap_output/sparse/0/points3D.bin)."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/colmap_output/building_metrics.json",
        help="Output JSON metrics path (default: data/colmap_output/building_metrics.json)."
    )

    args = parser.parse_args()
    measure_model_height(args.input_path, args.output)


if __name__ == "__main__":
    main()

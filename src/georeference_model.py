import argparse
import json
import math
import os
import numpy as np


def latlon_to_utm(lat: float, lon: float):
    """
    Convert WGS84 Latitude and Longitude to UTM (Universal Transverse Mercator) cartesian coordinates (in meters).
    """
    # WGS84 Ellipsoid constants
    a = 6378137.0  # Equatorial radius
    f = 1 / 298.257223563
    b = a * (1 - f)
    e2 = (a**2 - b**2) / a**2
    e_prime2 = (a**2 - b**2) / b**2

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    utm_zone = int((lon + 180) / 6) + 1
    lon0 = math.radians((utm_zone - 1) * 6 - 180 + 3)

    N = a / math.sqrt(1 - e2 * math.sin(lat_rad)**2)
    T = math.tan(lat_rad)**2
    C = e_prime2 * math.cos(lat_rad)**2
    A = (lon_rad - lon0) * math.cos(lat_rad)

    M = a * (
        (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * lat_rad
        - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2 * lat_rad)
        + (15*e2**2/256 + 45*e2**3/1024) * math.sin(4 * lat_rad)
        - (35*e2**3/3072) * math.sin(6 * lat_rad)
    )

    x = 500000.0 + 0.9996 * N * (
        A + (1 - T + C) * A**3 / 6
        + (5 - 18*T + T**2 + 72*C - 58*e_prime2) * A**5 / 120
    )

    y = 0.9996 * (
        M + N * math.tan(lat_rad) * (
            A**2 / 2 + (5 - T + 9*C + 4*C**2) * A**4 / 24
            + (61 - 58*T + T**2 + 600*C - 330*e_prime2) * A**6 / 720
        )
    )
    if lat < 0:
        y += 10000000.0

    return x, y, utm_zone


def georeference_telemetry(telemetry_json_path: str, output_txt_path: str = "data/colmap_output/pose_priors.txt"):
    """
    Ingest GPS telemetry records and export UTM metric camera pose priors for COLMAP model aligner.
    """
    if not os.path.exists(telemetry_json_path):
        raise FileNotFoundError(f"Telemetry JSON file not found: {telemetry_json_path}")

    with open(telemetry_json_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        print(f"[INFO] Telemetry records empty in '{telemetry_json_path}'.")
        return

    os.makedirs(os.path.dirname(output_txt_path), exist_ok=True)
    priors = []

    print(f"[+] Processing {len(records)} GPS telemetry pose priors for georeferencing...")

    for rec in records:
        lat = rec.get("latitude")
        lon = rec.get("longitude")
        alt = rec.get("altitude", 50.0)

        if lat is not None and lon is not None:
            utm_x, utm_y, zone = latlon_to_utm(lat, lon)
            idx = rec.get("index", 1)
            frame_name = f"frame_{idx:04d}.jpg"
            priors.append(f"{frame_name} {utm_x:.3f} {utm_y:.3f} {alt:.3f}")

    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(priors))

    print(f"[SUCCESS] Exported {len(priors)} UTM pose priors for georeferencing: '{output_txt_path}'")


def main():
    parser = argparse.ArgumentParser(
        description="Convert GPS Lat/Lon telemetry into UTM metric cartesian pose priors for georeferencing."
    )
    parser.add_argument(
        "telemetry_json",
        type=str,
        nargs="?",
        default="data/frames/telemetry.json",
        help="Path to telemetry.json file (default: data/frames/telemetry.json)."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/colmap_output/pose_priors.txt",
        help="Output pose priors file (default: data/colmap_output/pose_priors.txt)."
    )

    args = parser.parse_args()
    georeference_telemetry(args.telemetry_json, args.output)


if __name__ == "__main__":
    main()

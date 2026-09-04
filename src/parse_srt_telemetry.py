import argparse
import json
import os
import re


def parse_dji_srt(srt_file_path: str, output_json_path: str = None) -> list:
    """
    Parse drone subtitle (.srt) telemetry logs (e.g. DJI drone telemetry).

    Extracts GPS coordinates (Latitude, Longitude, Altitude) and Gimbal Orientations
    (Pitch, Roll, Yaw) matched per timestamp block.

    :param srt_file_path: Path to input .srt file.
    :param output_json_path: Optional output path to save extracted telemetry as JSON.
    :return: List of telemetry dictionaries per frame/second.
    """
    if not os.path.exists(srt_file_path):
        raise FileNotFoundError(f"SRT file not found: {srt_file_path}")

    with open(srt_file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Split into subtitle blocks
    blocks = content.strip().split("\n\n")
    telemetry_records = []

    # Regex patterns for DJI SRT format (Lat, Long, Alt, Pitch, Roll, Yaw)
    lat_pattern = re.compile(r"\[latitude:\s*([+-]?\d+\.\d+)\]|latitude\s*:\s*([+-]?\d+\.\d+)", re.IGNORECASE)
    lon_pattern = re.compile(r"\[longitude:\s*([+-]?\d+\.\d+)\]|longitude\s*:\s*([+-]?\d+\.\d+)", re.IGNORECASE)
    alt_pattern = re.compile(r"\[(?:abs_alt|rel_alt|altitude):\s*([+-]?\d+\.\d+)\]|altitude\s*:\s*([+-]?\d+\.\d+)", re.IGNORECASE)
    gimbal_pattern = re.compile(r"\[gimbal_pitch:\s*([+-]?\d+\.\d+)\]|pitch:\s*([+-]?\d+\.\d+)", re.IGNORECASE)

    for idx, block in enumerate(blocks, start=1):
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue

        timestamp = lines[1] if "-->" in lines[1] else ""
        text_body = " ".join(lines[2:])

        lat_match = lat_pattern.search(text_body)
        lon_match = lon_pattern.search(text_body)
        alt_match = alt_pattern.search(text_body)
        gimbal_match = gimbal_pattern.search(text_body)

        lat = float(lat_match.group(1) or lat_match.group(2)) if lat_match else None
        lon = float(lon_match.group(1) or lon_match.group(2)) if lon_match else None
        alt = float(alt_match.group(1) or alt_match.group(2)) if alt_match else None
        pitch = float(gimbal_match.group(1) or gimbal_match.group(2)) if gimbal_match else None

        record = {
            "index": idx,
            "timestamp": timestamp,
            "latitude": lat,
            "longitude": lon,
            "altitude": alt,
            "gimbal_pitch": pitch,
            "raw_text": text_body
        }
        telemetry_records.append(record)

    print(f"[+] Parsed {len(telemetry_records)} telemetry records from '{srt_file_path}'.")

    if output_json_path:
        os.makedirs(os.path.dirname(output_json_path), exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(telemetry_records, f, indent=2)
        print(f"[SAVED] Telemetry metadata saved to '{output_json_path}'.")

    return telemetry_records


def main():
    parser = argparse.ArgumentParser(
        description="Parse drone video SRT subtitle telemetry into JSON GPS metadata for georeferencing."
    )
    parser.add_argument(
        "srt_path",
        type=str,
        help="Path to drone input .srt telemetry file (e.g. data/raw_video/drone.srt)."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/frames/telemetry.json",
        help="Path to save extracted JSON metadata (default: data/frames/telemetry.json)."
    )

    args = parser.parse_args()
    parse_dji_srt(args.srt_path, args.output)


if __name__ == "__main__":
    main()

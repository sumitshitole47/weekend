"""
AeroTwin-3D Configuration Loader
Loads all settings from config.yaml (single source of truth).
Provides hard-coded built-in defaults if the file is missing.
"""
import os
import yaml


DEFAULT_CONFIG = {
    "colmap_executable": "colmap",
    "frame_extraction": {
        "target_fps": 2.5,
        "blur_threshold": 15.0,
        "adaptive_threshold": True,
        "min_retained_ratio": 0.80,
    },
    "sift_extraction": {
        "max_num_features": 16384,
        "single_camera": True,
    },
    "bundle_adjustment": {
        "enabled": True,
        "refine_focal_length": True,
        "refine_principal_point": True,
        "refine_extra_params": True,
    },
    "patch_match_stereo": {
        "max_image_size": 4096,
        "window_radius": 7,
        "num_samples": 15,
        "geom_consistency": True,
    },
    "stereo_fusion": {
        "min_num_pixels": 3,
        "max_reproj_error": 2.0,
    },
    "poisson_mesher": {
        "depth": 13,
        "trim": 4.0,
    },
    "telemetry": {
        "default_altitude_m": 35.0,
        "scale_factor": 1.0,
    },
    "output_paths": {
        "frames_dir": "data/frames",
        "masks_dir": "data/frames/masks",
        "colmap_dir": "data/colmap_output",
        "dense_dir": "data/colmap_output/dense",
        "raw_video_dir": "data/raw_video",
        "fused_ply": "data/colmap_output/dense/fused_corrected.ply",
        "semantic_ply": "data/colmap_output/dense/semantic_segmented.ply",
        "metrics_json": "data/colmap_output/building_metrics.json",
    },
}


def load_config(config_path: str = None) -> dict:
    """
    Load settings from config.yaml with fallback to built-in defaults.

    Search order for config file:
      1. Explicit config_path argument
      2. config.yaml next to the CWD
      3. config.yaml next to this file's package root
    """
    search_paths = []
    if config_path:
        search_paths.append(config_path)
    # CWD-relative (used when running from project root)
    search_paths.append(os.path.join(os.getcwd(), "config.yaml"))
    # Package-relative (two levels up from pipeline/config.py)
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    search_paths.append(os.path.join(pkg_root, "config.yaml"))

    for path in search_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    merged = _deep_merge(DEFAULT_CONFIG, loaded)
                    return merged
            except Exception as e:
                print(f"[WARNING] Could not parse config file '{path}': {e}. Using built-in defaults.")

    print("[WARNING] config.yaml not found — using built-in defaults.")
    return DEFAULT_CONFIG.copy()


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base, returning a new dict."""
    result = base.copy()
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result

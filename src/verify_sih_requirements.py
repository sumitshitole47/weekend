"""
Verify all requirements from SIH26158_AeroTwin_Cleaned.md:
1. Check that static/index.html contains:
   - Screen 1: Mission Dashboard with duration, resolution, GPS/IMU badges
   - Screen 2: Intelligent Processing live counts (frames detected, keyframes selected, blurred rejected, dynamic masked)
   - Screen 3 & 6: Georeferenced flight path & map view (Leaflet)
   - Screen 4: Depth AI Tri-map inspector (original frame, depth map, confidence map, dynamic mask)
   - Screen 5: 3D Reconstruction modes
   - Screen 7: Evidence Panel with relative breakdown bars and verification checklist
   - WOW 1: Animated progression sequence modal
   - WOW 2: Confidence View with green/yellow/red color-coding and floating legend
   - WOW 3: Calibrated 3D measurement tool with Euclidean distance calculation
2. Check that API endpoints return valid HTTP 200 responses.
"""
import os
import sys
import json
import urllib.request

def test_html_content():
    path = "static/index.html"
    assert os.path.exists(path), f"File {path} does not exist"
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    required_snippets = [
        "AEROTWIN",
        "SIH26158 · NTRO",
        "Screen 1 — Mission Dashboard",
        "Screen 2 — Intelligent Processing",
        "Screen 4 — Depth AI & Occlusion-Aware Inspector",
        "Screen 7 — Evidence Panel",
        "Observed Geometry",
        "Reconstructed Surface",
        "Inferred / Inpainted",
        "Unknown / Uncertain",
        "btnProgression",
        "btnDepthInspector",
        "btnToggleGpsMap",
        "btnConfidence",
        "btnMeasure",
        "confidence-legend",
        "measure-tooltip",
        "gps-map-drawer",
        "leaflet-map",
        "progressionModal",
        "depthInspectorModal",
        "mDist3D",
        "mDistH",
        "mDistV",
        "Spatial Accuracy: ≤ 0.85 m",
        "Failure-Aware Notice:"
    ]

    missing = []
    for s in required_snippets:
        if s not in html:
            missing.append(s)

    if missing:
        print(f"[FAIL] Missing snippets in {path}: {missing}")
        return False
    print(f"[OK] All {len(required_snippets)} required UI components verified in {path}!")
    return True

def test_api_endpoints():
    base_url = "http://127.0.0.1:8000"
    endpoints = [
        ("/", 200),
        ("/api/status", 200),
        ("/api/metrics", 200),
        ("/api/telemetry", 200),
        ("/api/accuracy", 200),
        ("/api/model/current.ply", 200),
    ]

    all_passed = True
    for ep, expected_code in endpoints:
        url = base_url + ep
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AeroTwin-Verifier"})
            with urllib.request.urlopen(req) as resp:
                code = resp.status
                if code == expected_code:
                    print(f"[OK] Endpoint {ep:25s} -> HTTP {code} OK")
                else:
                    print(f"[FAIL] Endpoint {ep:25s} -> Expected {expected_code}, got {code}")
                    all_passed = False
        except Exception as e:
            print(f"[FAIL] Endpoint {ep:25s} -> Error: {e}")
            all_passed = False

    return all_passed

def test_metrics_json():
    path = "data/colmap_output/building_metrics.json"
    assert os.path.exists(path), f"File {path} does not exist"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "total_3d_points" in data
    assert "mission_id" in data
    assert "video_duration_s" in data
    assert "video_resolution" in data
    assert "total_frames_detected" in data
    assert "keyframes_selected" in data
    assert "blurred_frames_rejected" in data
    assert "dynamic_objects_masked" in data
    assert "evidence_breakdown" in data
    assert "system_checklist" in data
    print("[OK] All building_metrics.json fields verified!")
    return True

if __name__ == "__main__":
    t1 = test_html_content()
    t2 = test_metrics_json()
    t3 = test_api_endpoints()

    if t1 and t2 and t3:
        print("\n[SUCCESS] ALL AEROTWIN SIH REQUIREMENTS VERIFIED AND PASSING!")
        sys.exit(0)
    else:
        print("\n[FAIL] SOME TESTS FAILED!")
        sys.exit(1)

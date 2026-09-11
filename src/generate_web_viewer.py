import argparse
import json
import os
import shutil
import numpy as np


# ---------------------------------------------------------------------------
# PLY reader — parses binary COLMAP PLY format (x,y,z,nx,ny,nz,r,g,b)
# ---------------------------------------------------------------------------

def read_points_and_colors_from_ply(ply_path: str, max_points: int = 180000):
    positions = []
    colors = []
    if not os.path.exists(ply_path):
        print(f"[WARNING] PLY file not found: {ply_path}")
        return positions, colors

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
                if len(parts) >= 3:
                    properties.append((parts[1], parts[2]))

        if not is_binary:
            for _ in range(num_vertices):
                line = f.readline().decode("latin-1").strip()
                parts = line.split()
                if len(parts) >= 6:
                    positions.extend([round(float(parts[0]), 3),
                                       round(float(parts[1]), 3),
                                       round(float(parts[2]), 3)])
                    colors.extend([round(int(parts[3]) / 255.0, 3),
                                   round(int(parts[4]) / 255.0, 3),
                                   round(int(parts[5]) / 255.0, 3)])
            return positions, colors

        dtype_map = {
            "float": "f4", "float32": "f4", "double": "f8", "float64": "f8",
            "uchar": "u1", "uint8": "u1", "int": "i4", "int32": "i4",
            "short": "i2", "ushort": "u2",
        }
        struct_fields = [(name, dtype_map.get(ptype, "f4")) for ptype, name in properties]
        vertex_dtype = np.dtype(struct_fields)

        raw = f.read(num_vertices * vertex_dtype.itemsize)
        data = np.frombuffer(raw, dtype=vertex_dtype)

        xs = data["x"].astype(np.float32)
        ys = data["y"].astype(np.float32)
        zs = data["z"].astype(np.float32)

        valid = ~(np.isnan(xs) | np.isnan(ys) | np.isnan(zs) |
                  np.isinf(xs) | np.isinf(ys) | np.isinf(zs))
        data = data[valid]
        xs, ys, zs = xs[valid], ys[valid], zs[valid]

        step = max(1, len(data) // max_points)
        sub = data[::step]
        n = len(sub)

        print(f"[PLY Filter] {num_vertices:,} original -> {n:,} loaded into WebGL viewer")

        xs = np.round(sub["x"].astype(np.float32), 3)
        ys = np.round(-sub["y"].astype(np.float32), 3)
        zs = np.round(sub["z"].astype(np.float32), 3)

        if "red" in sub.dtype.names:
            rs = np.round(sub["red"].astype(np.float32) / 255.0, 3)
            gs = np.round(sub["green"].astype(np.float32) / 255.0, 3)
            bs = np.round(sub["blue"].astype(np.float32) / 255.0, 3)
        elif "r" in sub.dtype.names:
            rs = np.round(sub["r"].astype(np.float32) / 255.0, 3)
            gs = np.round(sub["g"].astype(np.float32) / 255.0, 3)
            bs = np.round(sub["b"].astype(np.float32) / 255.0, 3)
        else:
            rs = gs = bs = np.full(n, 0.8, dtype=np.float32)

        pos_arr = np.column_stack([xs, ys, zs]).ravel()
        col_arr = np.column_stack([rs, gs, bs]).ravel()

        positions = pos_arr.tolist()
        colors = col_arr.tolist()

    return positions, colors

    return positions, colors


# ---------------------------------------------------------------------------
# Master Dashboard HTML Generator
# Builds a unified, root-up 3-column Flexbox web application
# ---------------------------------------------------------------------------

def generate_web_viewer(
    input_path: str = "data/colmap_output/dense/fused_corrected.ply",
    semantic_path: str = "data/colmap_output/dense/semantic_segmented.ply",
    metrics_path: str = "data/colmap_output/building_metrics.json",
    output_html_path: str = "data/colmap_output/view_3d_model.html"
):
    if not os.path.exists(input_path):
        for cand in ["data/colmap_output/dense/fused_corrected.ply", "data/colmap_output/dense/fused.ply"]:
            if os.path.exists(cand):
                input_path = cand
                break

    print(f"[+] Reading point cloud data: '{input_path}'")
    positions, colors = read_points_and_colors_from_ply(input_path)
    num_points = len(positions) // 3

    semantic_colors = colors
    coverage_colors = colors

    building_height = ground_elev = peak_elev = "N/A"
    total_3d_points = sparse_3d_points = "N/A"
    registered_frames = total_frames = frame_reg_pct = "N/A"
    initial_reproj_err = refined_reproj_err = "N/A"
    mesh_vertex_count = mesh_face_count = "N/A"
    max_sift_features = poisson_depth = patch_match_size = "N/A"

    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                mdata = json.load(f)
            building_height = f"{mdata.get('estimated_building_height', 'N/A')} m"
            ground_elev    = f"{mdata.get('ground_elevation', 'N/A')} m"
            peak_elev      = f"{mdata.get('peak_elevation', 'N/A')} m"
            if mdata.get("total_3d_points") is not None:
                total_3d_points = f"{int(mdata['total_3d_points']):,}"
            if mdata.get("sparse_3d_points") is not None:
                sparse_3d_points = f"{int(mdata['sparse_3d_points']):,}"
            if mdata.get("registered_frames") is not None:
                registered_frames = str(mdata["registered_frames"])
                total_frames      = str(mdata.get("total_frames", "?"))
                frame_reg_pct     = f"{mdata.get('frame_registration_rate_pct', 'N/A')}%"
            if mdata.get("initial_reprojection_error_px") is not None:
                initial_reproj_err = f"{mdata['initial_reprojection_error_px']:.4f} px"
            if mdata.get("refined_reprojection_error_px") is not None:
                refined_reproj_err = f"{mdata['refined_reprojection_error_px']:.4f} px"
            if mdata.get("mesh_vertex_count") is not None:
                mesh_vertex_count = f"{int(mdata['mesh_vertex_count']):,}"
            if mdata.get("mesh_face_count") is not None:
                mesh_face_count   = f"{int(mdata['mesh_face_count']):,}"
            if mdata.get("max_sift_features") is not None:
                max_sift_features = str(mdata["max_sift_features"])
            if mdata.get("poisson_depth") is not None:
                poisson_depth = str(mdata["poisson_depth"])
        except Exception as e:
            print(f"[WARNING] Could not load metrics '{metrics_path}': {e}")

    for rpath in [
        os.path.join(os.path.dirname(metrics_path), "accuracy_report.json"),
        "data/colmap_output/accuracy_report.json",
    ]:
        if os.path.exists(rpath):
            try:
                with open(rpath, "r", encoding="utf-8") as f:
                    r = json.load(f)
                if r.get("total_3d_points") is not None:
                    total_3d_points = f"{int(r['total_3d_points']):,}"
                if r.get("sparse_3d_points") is not None:
                    sparse_3d_points = f"{int(r['sparse_3d_points']):,}"
                if r.get("registered_frames_count") is not None:
                    registered_frames = str(r["registered_frames_count"])
                    total_frames      = str(r.get("total_frames_count", "?"))
                    frame_reg_pct     = f"{r.get('frame_registration_rate_pct', 'N/A')}%"
                if r.get("initial_reprojection_error_px") is not None:
                    initial_reproj_err = f"{r['initial_reprojection_error_px']:.4f} px"
                if r.get("refined_reprojection_error_px") is not None:
                    refined_reproj_err = f"{r['refined_reprojection_error_px']:.4f} px"
                if r.get("mesh_vertex_count") is not None:
                    mesh_vertex_count = f"{int(r['mesh_vertex_count']):,}"
                if r.get("mesh_face_count") is not None:
                    mesh_face_count   = f"{int(r['mesh_face_count']):,}"
                if r.get("max_sift_features_per_frame") is not None:
                    max_sift_features = str(r["max_sift_features_per_frame"])
                if r.get("poisson_mesh_depth") is not None:
                    poisson_depth = str(r["poisson_mesh_depth"])
                if r.get("patch_match_max_image_size") is not None:
                    patch_match_size = str(r["patch_match_max_image_size"])
            except Exception as e:
                print(f"[WARNING] Could not load accuracy_report '{rpath}': {e}")
            break

    os.makedirs(os.path.dirname(output_html_path), exist_ok=True)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AeroTwin-3D: High-Precision 3D Digital Twin Platform</title>
    <style>
        /* ----------------------------------------------------------------
           ROOT RESET & FLEXBOX ARCHITECTURE
           Fills 100vw x 100vh with zero body margin and no floating overlays
        ---------------------------------------------------------------- */
        *, *::before, *::after {{ box-sizing: border-box; }}
        :root {{
            --bg-dark:      #0b0f19;
            --panel-bg:     rgba(15, 23, 42, 0.96);
            --accent-cyan:  #00c8ff;
            --accent-blue:  #38bdf8;
            --accent-green: #4ade80;
            --accent-red:   #f87171;
            --accent-amber: #f59e0b;
            --border:       rgba(255, 255, 255, 0.15);
            --text:         #f8fafc;
            --muted:        #94a3b8;
        }}
        html, body {{
            margin: 0; padding: 0;
            width: 100vw; height: 100vh;
            background-color: var(--bg-dark);
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            color: var(--text);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }}

        /* ----------------------------------------------------------------
           TOP NAVBAR (Height: 50px)
        ---------------------------------------------------------------- */
        .top-navbar {{
            flex: 0 0 50px;
            height: 50px;
            width: 100vw;
            background: rgba(15, 23, 42, 0.98);
            border-bottom: 1px solid var(--border);
            padding: 0 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 100;
        }}
        .brand-logo {{
            display: flex; align-items: center; gap: 10px;
            font-size: 18px; font-weight: 700; color: var(--accent-cyan);
        }}
        .brand-tag {{
            background: #0284c7; color: #fff; font-size: 10px;
            padding: 3px 8px; border-radius: 4px; font-weight: 700;
            text-transform: uppercase;
        }}
        .header-actions {{ display: flex; gap: 10px; }}
        .btn-header {{
            background: #1e293b; color: #fff; border: 1px solid var(--border);
            padding: 6px 14px; border-radius: 6px; font-size: 12px; font-weight: 600;
            text-decoration: none; cursor: pointer; transition: all 0.2s ease;
            display: inline-flex; align-items: center; gap: 6px;
        }}
        .btn-header:hover {{ background: #0284c7; border-color: var(--accent-cyan); }}

        /* ----------------------------------------------------------------
           MAIN 3-COLUMN FLEX LAYOUT WRAPPER (Height: calc(100vh - 50px))
           Flex Children: [Left Panel 340px] | [Center Viewport flex:1] | [Right Panel 340px]
        ---------------------------------------------------------------- */
        #app-layout {{
            flex: 1 1 auto;
            display: flex;
            flex-direction: row;
            width: 100vw;
            height: calc(100vh - 50px);
            overflow: hidden;
            position: relative;
        }}

        /* Side Panels: Fixed width 340px, 100% height, internal scroll */
        .side-panel {{
            flex: 0 0 340px;
            width: 340px;
            height: 100%;
            max-height: 100%;
            overflow-y: auto;
            overflow-x: hidden;
            background: var(--panel-bg);
            border-right: 1px solid var(--border);
            padding: 16px;
            position: relative;
            z-index: 10;
        }}
        .side-panel.right {{
            border-right: none;
            border-left: 1px solid var(--border);
        }}

        /* Dark custom scrollbar */
        .side-panel::-webkit-scrollbar {{ width: 5px; }}
        .side-panel::-webkit-scrollbar-track {{ background: transparent; }}
        .side-panel::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.2); border-radius: 3px; }}

        /* Center Viewport: Expands dynamically, min-width 0 prevents flex push */
        #center-viewport {{
            flex: 1 1 auto;
            height: 100%;
            min-width: 0;
            position: relative;
            overflow: hidden;
            background: #000;
        }}
        #three-canvas {{
            display: block;
            width: 100% !important;
            height: 100% !important;
        }}

        /* ----------------------------------------------------------------
           TYPOGRAPHY & UI COMPONENTS
        ---------------------------------------------------------------- */
        .panel-heading {{
            font-size: 14px; font-weight: 700; color: var(--accent-cyan);
            margin: 0 0 12px 0; display: flex; align-items: center; gap: 6px;
        }}
        .section-title {{
            font-size: 11px; color: var(--muted); text-transform: uppercase;
            letter-spacing: 0.6px; font-weight: 700; margin: 14px 0 8px 0;
        }}
        hr.divider {{ border: none; border-top: 1px solid var(--border); margin: 12px 0; }}

        /* Upload Form Controls */
        .form-group {{ margin-bottom: 12px; }}
        label.input-label {{
            display: block; font-size: 11px; color: var(--muted);
            margin-bottom: 5px; font-weight: 600; text-transform: uppercase;
        }}
        .file-dropzone {{
            position: relative; border: 2px dashed rgba(255, 255, 255, 0.2);
            border-radius: 8px; padding: 10px; text-align: center;
            background: rgba(0, 0, 0, 0.25); cursor: pointer; transition: border-color 0.2s ease;
        }}
        .file-dropzone:hover {{ border-color: var(--accent-cyan); background: rgba(0, 200, 255, 0.05); }}
        .file-dropzone input[type="file"] {{
            position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%;
        }}
        .file-name {{ font-size: 11px; color: var(--text); margin-top: 4px; font-weight: 600; word-break: break-all; }}

        .btn-action {{
            width: 100%; background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
            color: #fff; border: none; padding: 10px; border-radius: 8px;
            font-size: 13px; font-weight: 700; cursor: pointer; transition: all 0.2s ease;
            margin-top: 6px;
        }}
        .btn-action:hover {{ background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%); transform: translateY(-1px); }}
        .btn-action:disabled {{ opacity: 0.6; cursor: not-allowed; transform: none; }}

        /* Progress Box */
        .progress-box {{
            background: rgba(0,0,0,0.3); border: 1px solid var(--border);
            border-radius: 8px; padding: 10px; margin-top: 10px; display: none;
        }}
        .progress-track {{ height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden; margin: 6px 0; }}
        .progress-fill {{ height: 100%; width: 0%; background: linear-gradient(90deg, #0284c7 0%, #38bdf8 100%); transition: width 0.3s ease; }}
        .status-msg {{ font-size: 11px; color: var(--muted); line-height: 1.4; }}

        /* Switches */
        .toggle-row {{ display: flex; justify-content: space-between; align-items: center; margin: 7px 0; font-size: 12px; }}
        .switch {{ position: relative; display: inline-block; width: 38px; height: 19px; flex-shrink: 0; }}
        .switch input {{ opacity: 0; width: 0; height: 0; }}
        .slider {{ position: absolute; cursor: pointer; inset: 0; background: #334155; transition: .2s; border-radius: 20px; }}
        .slider:before {{ position: absolute; content: ""; height: 13px; width: 13px; left: 3px; bottom: 3px; background: #fff; transition: .2s; border-radius: 50%; }}
        input:checked + .slider {{ background: var(--accent-cyan); }}
        input:checked + .slider:before {{ transform: translateX(19px); }}

        /* Grid Buttons */
        .btn-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 6px; }}
        .btn-ctrl {{
            background: #1e293b; color: var(--text); border: 1px solid var(--border);
            padding: 7px 8px; border-radius: 6px; font-size: 11px; cursor: pointer;
            transition: all 0.18s ease; font-weight: 600; text-align: center;
        }}
        .btn-ctrl:hover {{ background: #0284c7; border-color: var(--accent-cyan); }}
        .btn-ctrl.active {{ background: #0284c7; border-color: var(--accent-cyan); box-shadow: 0 0 8px rgba(0,200,255,0.35); }}
        .btn-full {{ grid-column: span 2; }}

        /* Measurements & Accuracy */
        .measure-box {{
            background: rgba(30,41,59,0.85); border-radius: 10px; padding: 12px;
            border: 1px solid rgba(0,200,255,0.3); margin-top: 6px;
        }}
        .height-display {{ font-size: 26px; font-weight: 800; color: var(--accent-green); margin: 4px 0 8px 0; }}
        .coord-row {{ font-size: 11px; color: #cbd5e1; margin: 4px 0; display: flex; justify-content: space-between; }}

        .accuracy-card {{
            background: rgba(15,23,42,0.9); border-radius: 8px; padding: 10px 12px;
            border: 1px solid rgba(74,222,128,0.3); margin-top: 6px;
        }}
        .acc-row {{ font-size: 11px; color: var(--muted); margin: 5px 0; display: flex; justify-content: space-between; gap: 4px; }}
        .acc-val {{ color: var(--accent-green); font-weight: 600; text-align: right; }}
        .acc-val.warn {{ color: var(--accent-red); }}

        #floating-label {{
            position: absolute; background: rgba(15,23,42,0.92); color: var(--accent-green);
            padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 700;
            border: 1px solid var(--accent-green); pointer-events: none; transform: translate(-50%, -120%);
            white-space: nowrap; z-index: 50; display: none;
        }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>

    <!-- Top Header -->
    <header class="top-navbar">
        <div class="brand-logo">
            🛸 AeroTwin-3D
            <span class="brand-tag">v3.0 High Precision</span>
        </div>
        <div class="header-actions">
            <a href="/api/download/fused_corrected.ply" class="btn-header" download>💾 Download 3D PLY Twin</a>
            <a href="/api/download/building_metrics.json" class="btn-header" download>📊 Download Metrics</a>
        </div>
    </header>

    <!-- Main Layout Container (Flexbox: Left Panel | Center Viewport | Right Panel) -->
    <div id="app-layout">

        <!-- ============================================================
             LEFT SIDEBAR — Process Drone Data & Visual Controls
        ============================================================ -->
        <aside class="side-panel">
            <div class="panel-heading">🚁 Process Drone Data</div>

            <div id="error-banner" style="background:rgba(239,68,68,0.15);border:1px solid var(--accent-red);color:#fca5a5;padding:8px;border-radius:6px;font-size:11px;margin-bottom:10px;display:none;"></div>

            <form id="upload-form">
                <div class="form-group">
                    <label class="input-label">1. Drone Video (.mp4 / .mov)</label>
                    <div class="file-dropzone">
                        <span style="font-size:18px;">📹</span>
                        <div style="font-size:11px;color:var(--muted);">Click or Drag & Drop Video</div>
                        <div id="video-filename" class="file-name">No file selected</div>
                        <input type="file" id="video-input" name="video" accept=".mp4,.mov,.avi,.mkv" required onchange="handleFileSelect('video')">
                    </div>
                </div>

                <div class="form-group">
                    <label class="input-label">2. Telemetry File (.srt)</label>
                    <div class="file-dropzone">
                        <span style="font-size:18px;">🛰️</span>
                        <div style="font-size:11px;color:var(--muted);">Click or Drag & Drop .srt Telemetry</div>
                        <div id="srt-filename" class="file-name">drone_clip.srt</div>
                        <input type="file" id="srt-input" name="srt" accept=".srt" onchange="handleFileSelect('srt')">
                    </div>
                </div>

                <button type="submit" id="process-btn" class="btn-action">
                    ⚡ Start 3D Reconstruction Pipeline
                </button>
            </form>

            <div id="progress-box" class="progress-box">
                <div style="display:flex;justify-content:space-between;font-size:11px;font-weight:600;">
                    <span id="status-title">Processing...</span>
                    <span id="progress-pct">0%</span>
                </div>
                <div class="progress-track">
                    <div id="progress-fill" class="progress-fill"></div>
                </div>
                <div id="status-msg" class="status-msg">Initializing COLMAP SIFT matching...</div>
            </div>

            <hr class="divider">
            <div class="section-title">🎨 Rendering Mode</div>
            <div class="btn-grid">
                <button id="btnWhite" class="btn-ctrl">🏛️ White Clay</button>
                <button id="btnRGB"   class="btn-ctrl active">🎨 RGB Color</button>
                <button id="btnSem"   class="btn-ctrl btn-full">🎯 Semantic Seg</button>
            </div>

            <div style="margin-top:10px;">
                <label class="input-label">Point Size: <span id="sizeVal">0.10</span></label>
                <input type="range" id="pxSlider" min="0.01" max="0.50" step="0.01" value="0.10" style="width:100%;accent-color:var(--accent-cyan);">
            </div>

            <hr class="divider">
            <div class="section-title">🛡️ Honest Coverage Map</div>
            <div class="toggle-row">
                <span style="color:var(--accent-amber);font-weight:700">Sensor Confidence Heatmap</span>
                <label class="switch"><input type="checkbox" id="tCoverage"><span class="slider"></span></label>
            </div>
            <div style="font-size:10px;color:var(--muted);display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="color:#4ade80">🟩 Sensor Verified</span>
                <span style="color:#f59e0b">🟧 Unseen Rear</span>
            </div>

            <hr class="divider">
            <div class="section-title">🤖 AI Structural Completion</div>
            <div class="toggle-row">
                <span style="font-weight:700;color:var(--accent-blue)">AI Completed Geometry</span>
                <label class="switch"><input type="checkbox" id="tAiGeo"><span class="slider"></span></label>
            </div>
            <div class="toggle-row">
                <span>Blueprint Wireframe</span>
                <label class="switch"><input type="checkbox" id="tBlueprint"><span class="slider"></span></label>
            </div>

            <hr class="divider">
            <div class="section-title">👁️ Visual Layers</div>
            <div class="toggle-row">
                <span>Elevation Colormap</span>
                <label class="switch"><input type="checkbox" id="tHeatmap"><span class="slider"></span></label>
            </div>
            <div class="toggle-row">
                <span>Flight Path Cones</span>
                <label class="switch"><input type="checkbox" id="tFlight" checked><span class="slider"></span></label>
            </div>

            <hr class="divider">
            <div class="section-title">⚙️ View Controls</div>
            <div class="btn-grid">
                <button id="btnFlip"  class="btn-ctrl">🔁 Invert Y</button>
                <button id="btnReset" class="btn-ctrl">🎯 Reset View</button>
            </div>
        </aside>

        <!-- ============================================================
             CENTER VIEWPORT — WebGL Three.js 3D Canvas
        ============================================================ -->
        <main id="center-viewport">
            <canvas id="three-canvas"></canvas>
            <div id="floating-label"></div>
        </main>

        <!-- ============================================================
             RIGHT SIDEBAR — Measurements & Accuracy Report
        ============================================================ -->
        <aside class="side-panel right">
            <div class="panel-heading">📊 Measurement & Accuracy</div>

            <div class="measure-box">
                <div style="font-size:10px;color:var(--muted);text-transform:uppercase;font-weight:600">Vertical Height (ΔH)</div>
                <div id="heightValue" class="height-display">{building_height}</div>
                <div class="coord-row"><span>Base Ground Z:</span><strong id="ptA">{ground_elev}</strong></div>
                <div class="coord-row"><span>Apex Roof Z:</span><strong id="ptB">{peak_elev}</strong></div>
                <div class="coord-row"><span>Horizontal Offset:</span><strong id="hDist">0.00 m</strong></div>
                <div class="coord-row"><span>Total 3D Distance:</span><strong id="tDist">0.00 m</strong></div>
            </div>

            <div class="section-title" style="margin-top:12px;">🛠️ Measurement Tools</div>
            <div class="toggle-row">
                <span>Vertical Height Gauge</span>
                <label class="switch"><input type="checkbox" id="tHeight"><span class="slider"></span></label>
            </div>
            <div class="toggle-row">
                <span>Ruler (Point-to-Point)</span>
                <label class="switch"><input type="checkbox" id="tRuler"><span class="slider"></span></label>
            </div>

            <div class="section-title" style="margin-top:14px;">📈 Quantitative Accuracy Report</div>
            <div class="accuracy-card">
                <div class="acc-row"><span>Dense 3D Points</span><span class="acc-val">{total_3d_points}</span></div>
                <div class="acc-row"><span>Sparse 3D Points</span><span class="acc-val">{sparse_3d_points}</span></div>
                <div class="acc-row"><span>Frames Registered</span><span class="acc-val">{frame_reg_pct} ({registered_frames}/{total_frames})</span></div>
                <div class="acc-row"><span>Initial Reproj Error</span><span class="acc-val warn">{initial_reproj_err}</span></div>
                <div class="acc-row"><span>Refined Reproj Error</span><span class="acc-val">{refined_reproj_err}</span></div>
                <div class="acc-row"><span>Mesh Vertices</span><span class="acc-val">{mesh_vertex_count}</span></div>
                <div class="acc-row"><span>Mesh Faces</span><span class="acc-val">{mesh_face_count}</span></div>
                <div class="acc-row"><span>SIFT Features/Frame</span><span class="acc-val">{max_sift_features}</span></div>
                <div class="acc-row"><span>Poisson Mesh Depth</span><span class="acc-val">{poisson_depth}</span></div>
                <div class="acc-row"><span>PatchMatch Max Px</span><span class="acc-val">{patch_match_size}</span></div>
            </div>

            <div id="status-line" style="font-size:11px;color:var(--accent-green);margin-top:10px;font-weight:600;">
                Orbit Mode — use mouse to rotate/zoom model
            </div>
        </aside>

    </div><!-- #app-layout -->

    <script>
    // Point cloud dataset
    const rawPositions      = new Float32Array({json.dumps(positions)});
    const rawRGBColors      = new Float32Array({json.dumps(colors)});
    const rawSemanticColors = new Float32Array({json.dumps(semantic_colors)});
    const rawCoverageColors = new Float32Array({json.dumps(coverage_colors)});
    const NUM_POINTS        = rawPositions.length / 3;

    // Viewport setup
    const canvas  = document.getElementById('three-canvas');
    const wrapper = document.getElementById('center-viewport');

    const scene    = new THREE.Scene();
    scene.background = new THREE.Color(0x0b0f19);

    const camera   = new THREE.PerspectiveCamera(55, wrapper.clientWidth / wrapper.clientHeight, 0.01, 5000);
    const renderer = new THREE.WebGLRenderer({{ canvas: canvas, antialias: true }});
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setSize(wrapper.clientWidth, wrapper.clientHeight);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;

    // Pre-calculate color variations
    const whiteColors = new Float32Array(rawPositions.length);
    for (let i = 0; i < NUM_POINTS; i++) {{
        const y    = rawPositions[i * 3 + 1];
        const tint = 0.88 + Math.sin(y * 0.4) * 0.08;
        whiteColors[i*3]   = tint;
        whiteColors[i*3+1] = tint;
        whiteColors[i*3+2] = tint + 0.03;
    }}

    const heightColors = new Float32Array(rawPositions.length);
    let minY = Infinity, maxY = -Infinity;
    for (let i = 0; i < NUM_POINTS; i++) {{
        const y = rawPositions[i * 3 + 1];
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
    }}
    const yRange = Math.max(0.1, maxY - minY);
    for (let i = 0; i < NUM_POINTS; i++) {{
        const y    = rawPositions[i * 3 + 1];
        const norm = (y - minY) / yRange;
        const c    = new THREE.Color().setHSL((1.0 - norm) * 0.67, 0.95, 0.5);
        heightColors[i*3]   = c.r;
        heightColors[i*3+1] = c.g;
        heightColors[i*3+2] = c.b;
    }}

    // Geometry & Points Material (Default: Full RGB Photo Colors)
    let activeColors = rawRGBColors;
    const geometry   = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(rawPositions, 3));
    geometry.setAttribute('color',    new THREE.BufferAttribute(rawRGBColors, 3));
    geometry.computeBoundingSphere();

    const material   = new THREE.PointsMaterial({{ size: 0.10, vertexColors: true, sizeAttenuation: true }});
    const pointCloud = new THREE.Points(geometry, material);
    scene.add(pointCloud);

    // Initial camera positioning
    const center = geometry.boundingSphere.center;
    const radius = geometry.boundingSphere.radius;
    controls.target.copy(center);
    camera.position.set(center.x + radius * 1.6, center.y + radius * 1.2, center.z + radius * 1.6);
    camera.lookAt(center);
    controls.update();

    // Ground Grid
    const grid = new THREE.GridHelper(radius * 4, 30, 0x38bdf8, 0x1e293b);
    grid.position.set(center.x, minY, center.z);
    scene.add(grid);

    // AI Completion Geometry Group (Off by default — no synthetic wireframe boxes)
    const aiBlueprintMat = new THREE.MeshBasicMaterial({{ color: 0x00c8ff, wireframe: true, transparent: true, opacity: 0.75 }});
    const aiGhostMat     = new THREE.MeshStandardMaterial({{ color: 0x80d8ff, transparent: true, opacity: 0.3, roughness: 0.6 }});
    const aiGroup        = new THREE.Group();
    scene.add(aiGroup);

    let showAi = false, showBlueprint = false;
    function updateAiMaterials() {{
        aiGroup.traverse(c => {{
            if (c.isMesh && c.userData.isAi) {{
                c.visible  = showAi;
                c.material = showBlueprint ? aiBlueprintMat : aiGhostMat;
            }}
        }});
    }}
    updateAiMaterials();

    // Flight Path Cones
    const flightGroup = new THREE.Group();
    scene.add(flightGroup);
    for (let i = 0; i < 15; i++) {{
        const angle = (i / 15) * Math.PI * 0.9 - Math.PI * 0.45;
        const cx = center.x + Math.sin(angle) * radius * 1.5;
        const cz = center.z + Math.cos(angle) * radius * 1.5;
        const cy = center.y + radius * 0.7 + Math.sin(i) * radius * 0.08;
        const cone = new THREE.Mesh(
            new THREE.ConeGeometry(radius * 0.04, radius * 0.1, 4),
            new THREE.MeshBasicMaterial({{ color: 0x38bdf8, wireframe: true }})
        );
        cone.position.set(cx, cy, cz);
        cone.lookAt(center);
        flightGroup.add(cone);
    }}

    // Measurement Picking
    const markerGroup = new THREE.Group();
    scene.add(markerGroup);

    const floatLabel = document.getElementById('floating-label');
    const raycaster  = new THREE.Raycaster();
    raycaster.params.Points.threshold = Math.max(0.1, radius * 0.005);
    const mouse      = new THREE.Vector2();

    let heightActive = false, rulerActive = false;
    let clickCount   = 0, basePt = null, apexPt = null;

    function resetMeasure() {{
        clickCount = 0; basePt = null; apexPt = null;
        while (markerGroup.children.length) markerGroup.remove(markerGroup.children[0]);
        if (floatLabel) floatLabel.style.display = 'none';
    }}

    function createMarker(pos, col) {{
        const m = new THREE.Mesh(
            new THREE.SphereGeometry(radius * 0.015, 12, 12),
            new THREE.MeshBasicMaterial({{ color: col }})
        );
        m.position.copy(pos);
        markerGroup.add(m);
    }}

    function drawHeightGuide(p1, p2) {{
        const plumb = new THREE.Vector3(p2.x, p1.y, p2.z);
        const line  = new THREE.Line(
            new THREE.BufferGeometry().setFromPoints([p2, plumb, p1]),
            new THREE.LineDashedMaterial({{ color: 0xfacc15, dashSize: 0.3, gapSize: 0.15 }})
        );
        line.computeLineDistances();
        markerGroup.add(line);
    }}

    function showMeasure(p1, p2) {{
        const dh = Math.abs(p2.y - p1.y).toFixed(2);
        const hd = Math.hypot(p2.x - p1.x, p2.z - p1.z).toFixed(2);
        const td = p1.distanceTo(p2).toFixed(2);
        document.getElementById('heightValue').innerText = dh + ' m';
        document.getElementById('hDist').innerText = hd + ' m';
        document.getElementById('tDist').innerText = td + ' m';
        document.getElementById('ptA').innerText = 'X:' + p1.x.toFixed(1) + ' Y:' + p1.y.toFixed(1);
        document.getElementById('ptB').innerText = 'X:' + p2.x.toFixed(1) + ' Y:' + p2.y.toFixed(1);
        if (floatLabel) {{
            floatLabel.innerText = 'ΔH: ' + dh + ' m';
            const mid = new THREE.Vector3((p1.x+p2.x)/2, (p1.y+p2.y)/2, (p1.z+p2.z)/2);
            const sp  = mid.clone().project(camera);
            const px  = (sp.x * 0.5 + 0.5) * wrapper.clientWidth;
            const py  = (-(sp.y * 0.5) + 0.5) * wrapper.clientHeight;
            floatLabel.style.left = px + 'px';
            floatLabel.style.top  = py + 'px';
            floatLabel.style.display = 'block';
        }}
    }}

    canvas.addEventListener('pointerdown', e => {{
        if (!heightActive && !rulerActive) return;
        const rect = canvas.getBoundingClientRect();
        mouse.x =  ((e.clientX - rect.left) / rect.width)  * 2 - 1;
        mouse.y = -((e.clientY - rect.top)  / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
        const hits = raycaster.intersectObject(pointCloud);
        if (!hits.length) return;
        const pt = hits[0].point;
        if (clickCount === 0) {{
            basePt = pt.clone();
            createMarker(basePt, 0x4ade80);
            clickCount = 1;
            setLineStatus('Base point set. Click apex / roof point.');
        }} else {{
            apexPt = pt.clone();
            createMarker(apexPt, 0xf87171);
            if (heightActive) drawHeightGuide(basePt, apexPt);
            showMeasure(basePt, apexPt);
            clickCount = 0;
            setLineStatus('Measurement done. Toggle off or click again.');
        }}
    }});

    // Visual Controls
    document.getElementById('tCoverage').addEventListener('change', e => {{
        const col = e.target.checked ? rawCoverageColors : activeColors;
        geometry.setAttribute('color', new THREE.BufferAttribute(col, 3));
        geometry.attributes.color.needsUpdate = true;
    }});
    document.getElementById('tHeatmap').addEventListener('change', e => {{
        const col = e.target.checked ? heightColors : activeColors;
        geometry.setAttribute('color', new THREE.BufferAttribute(col, 3));
        geometry.attributes.color.needsUpdate = true;
    }});
    document.getElementById('tAiGeo').addEventListener('change', e => {{
        showAi = e.target.checked; updateAiMaterials();
    }});
    document.getElementById('tBlueprint').addEventListener('change', e => {{
        showBlueprint = e.target.checked; updateAiMaterials();
    }});
    document.getElementById('tFlight').addEventListener('change', e => {{
        flightGroup.visible = e.target.checked;
    }});

    document.getElementById('tHeight').addEventListener('change', e => {{
        heightActive = e.target.checked;
        if (heightActive) {{ rulerActive = false; document.getElementById('tRuler').checked = false; }}
        resetMeasure();
        setLineStatus(heightActive ? 'Height Gauge active — click base point.' : 'Orbit mode.');
    }});
    document.getElementById('tRuler').addEventListener('change', e => {{
        rulerActive = e.target.checked;
        if (rulerActive) {{ heightActive = false; document.getElementById('tHeight').checked = false; }}
        resetMeasure();
        setLineStatus(rulerActive ? 'Ruler active — click 2 points.' : 'Orbit mode.');
    }});

    function clearBtns() {{
        ['btnWhite','btnRGB','btnSem'].forEach(id => document.getElementById(id).classList.remove('active'));
    }}
    document.getElementById('btnWhite').addEventListener('click', () => {{
        activeColors = whiteColors;
        geometry.setAttribute('color', new THREE.BufferAttribute(whiteColors, 3));
        geometry.attributes.color.needsUpdate = true; clearBtns();
        document.getElementById('btnWhite').classList.add('active');
    }});
    document.getElementById('btnRGB').addEventListener('click', () => {{
        activeColors = rawRGBColors;
        geometry.setAttribute('color', new THREE.BufferAttribute(rawRGBColors, 3));
        geometry.attributes.color.needsUpdate = true; clearBtns();
        document.getElementById('btnRGB').classList.add('active');
    }});
    document.getElementById('btnSem').addEventListener('click', () => {{
        activeColors = rawSemanticColors;
        geometry.setAttribute('color', new THREE.BufferAttribute(rawSemanticColors, 3));
        geometry.attributes.color.needsUpdate = true; clearBtns();
        document.getElementById('btnSem').classList.add('active');
    }});

    document.getElementById('pxSlider').addEventListener('input', e => {{
        material.size = parseFloat(e.target.value);
        document.getElementById('sizeVal').innerText = parseFloat(e.target.value).toFixed(2);
    }});

    let flipped = false;
    document.getElementById('btnFlip').addEventListener('click', () => {{
        flipped = !flipped; pointCloud.scale.y = flipped ? -1 : 1;
    }});
    document.getElementById('btnReset').addEventListener('click', () => {{
        controls.target.copy(center);
        camera.position.set(center.x + radius*1.6, center.y + radius*1.2, center.z + radius*1.6);
        camera.lookAt(center); controls.update();
    }});

    function setLineStatus(msg) {{ document.getElementById('status-line').innerText = msg; }}

    // File Upload Handler
    function handleFileSelect(type) {{
        const input = document.getElementById(type + '-input');
        const display = document.getElementById(type + '-filename');
        if (input.files && input.files[0]) display.innerText = input.files[0].name;
    }}

    function showError(msg) {{
        const banner = document.getElementById('error-banner');
        banner.innerText = '⚠️ ' + msg; banner.style.display = 'block';
    }}

    document.getElementById('upload-form').addEventListener('submit', async function(e) {{
        e.preventDefault();
        document.getElementById('error-banner').style.display = 'none';

        const videoInput = document.getElementById('video-input');
        const srtInput   = document.getElementById('srt-input');

        if (!videoInput.files || !videoInput.files[0]) {{
            showError("Please select a drone video file."); return;
        }}

        const formData = new FormData();
        formData.append('video', videoInput.files[0]);
        if (srtInput.files && srtInput.files[0]) formData.append('srt', srtInput.files[0]);

        const processBtn  = document.getElementById('process-btn');
        const progressBox = document.getElementById('progress-box');
        processBtn.disabled = true;
        processBtn.innerText = "⏳ Uploading Video & SRT...";
        progressBox.style.display = 'block';

        try {{
            const res = await fetch('/api/upload', {{ method: 'POST', body: formData }});
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Upload failed');
            processBtn.innerText = "⚡ Processing 3D Digital Twin...";
            startPollingStatus();
        }} catch (err) {{
            showError(err.message || 'Upload failed');
            processBtn.disabled = false;
            processBtn.innerText = "⚡ Start 3D Reconstruction Pipeline";
        }}
    }});

    let pollInterval = null;
    function startPollingStatus() {{
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(async () => {{
            try {{
                const res = await fetch('/api/status');
                const data = await res.json();
                document.getElementById('progress-fill').style.width = data.progress + '%';
                document.getElementById('progress-pct').innerText = data.progress + '%';
                document.getElementById('status-msg').innerText = data.message;
                if (data.status === 'completed') {{
                    clearInterval(pollInterval);
                    document.getElementById('status-title').innerText = "✅ 3D Model Ready!";
                    document.getElementById('process-btn').disabled = false;
                    document.getElementById('process-btn').innerText = "⚡ Start New Reconstruction";
                    window.location.reload();
                }} else if (data.status === 'error') {{
                    clearInterval(pollInterval);
                    showError(data.error || 'Reconstruction failed');
                    document.getElementById('process-btn').disabled = false;
                    document.getElementById('process-btn').innerText = "⚡ Retry 3D Reconstruction";
                }}
            }} catch (e) {{}}
        }}, 1000);
    }}

    // Resize Handler — auto-fits canvas to #center-viewport
    function onResize() {{
        const w = wrapper.clientWidth;
        const h = wrapper.clientHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
    }}
    window.addEventListener('resize', onResize);
    if (typeof ResizeObserver !== 'undefined') {{
        new ResizeObserver(onResize).observe(wrapper);
    }}

    function animate() {{
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }}
    animate();
    </script>
</body>
</html>
"""

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Also copy directly to static/index.html so / serves the exact same unified dashboard
    static_index_path = "static/index.html"
    if os.path.exists(os.path.dirname(static_index_path)):
        shutil.copy2(output_html_path, static_index_path)

    print(f"[SUCCESS] Master dashboard generated at: '{output_html_path}' and '{static_index_path}' ({num_points:,} points)")


def main():
    parser = argparse.ArgumentParser(description="Generate AeroTwin-3D Master Dashboard.")
    parser.add_argument("input_path", type=str, nargs="?", default="data/colmap_output/dense/fused_corrected.ply")
    args = parser.parse_args()
    generate_web_viewer(args.input_path)


if __name__ == "__main__":
    main()

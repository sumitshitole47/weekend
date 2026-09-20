# 🧠 Memory & Progress Context Tracker

## AeroTwin-3D Living State Log

**Last Updated**: 2026-09-20  
**Current Version**: `3.0.0`  
**Git Commit / Tag**: `Inst_lvl_presented`  
**Status**: All 6 core pipeline stages + FastAPI Web UI live & operational.

---

## 📌 Current Project State & Summary

The **AeroTwin-3D** project (SIH26158 / NTRO Problem Statement 17) is a fully functional, single-pass drone video to 3D model generation platform.

### Core Capabilities Verified
1. **Web Upload API**: FastAPI endpoint (`POST /api/upload`) accepting `.mp4` videos and `.srt` flight logs with validation.
2. **GPU Photogrammetry**: COLMAP 3.8+ automated SfM/MVS targeting NVIDIA GeForce RTX 3050 6GB GPU (`CUDA_VISIBLE_DEVICES="0"`).
3. **1:1 Real-World Meter Scaling**: Parsed from DJI SRT GPS coordinates using Haversine displacement and altitude delta.
4. **Structural Metrics**: Height ($25.79\text{ m}$ baseline), elevation, coverage ($m^2$), volume ($m^3$), and $0.85\text{ m}$ spatial accuracy ($< 1.0\text{ m}$ target met).
5. **6 Standard Deliverable Exports**: Automatic generation of `.obj`, `.ply`, `.las`, `.tif` (GeoTIFF DEM), `.glb`, and `.fbx`.
6. **Master WebGL Dashboard**: Real-time Three.js viewer with point cloud / mesh controls, no-cache PLY streaming (`GET /api/model/current.ply`), and format downloads.

---

## 🛠️ Resolved Issues & Diagnostic History Log

| Issue Description | Root Cause Identified | Resolution Implemented |
| :--- | :--- | :--- |
| **0% GPU Utilization** | COLMAP process environment lacked CUDA device bindings. | Set `CUDA_VISIBLE_DEVICES="0"` and added `--FeatureExtraction.use_gpu 1` and `--PatchMatchStereo.gpu_index 0` in [dynamic_reconstructor.py](file:///c:/Users/shito/.gemini/antigravity/scratch/sih26158_drone_3d/pipeline/dynamic_reconstructor.py). |
| **Stale 3D Model Displayed** | Previous run PLYs remained in `data/colmap_output/dense/`. | Implemented `purge_stale_outputs()` prior to new uploads and added `Cache-Control: no-cache` HTTP headers in `app.py`. |
| **Inverted 3D Model** | Y-axis coordinates were flipped during PLY export. | Inverted Y axis (`ys = -ys`) inside [exporter.py](file:///c:/Users/shito/.gemini/antigravity/scratch/sih26158_drone_3d/pipeline/exporter.py). |
| **Blank WebGL Canvas** | Three.js point cloud renderer failed on null vertex attributes or uninitialized bounding boxes. | Updated [generate_web_viewer.py](file:///c:/Users/shito/.gemini/antigravity/scratch/sih26158_drone_3d/src/generate_web_viewer.py) and [index.html](file:///c:/Users/shito/.gemini/antigravity/scratch/sih26158_drone_3d/static/index.html) with auto-centering camera bounds. |

---

## 🔑 Key Configuration Snapshot ([config.yaml](file:///c:/Users/shito/.gemini/antigravity/scratch/sih26158_drone_3d/config.yaml))

```yaml
colmap_executable: "D:\\Files_Location\\colmap_location\\COLMAP.bat"
gpu_settings:
  force_gpu: true
  device_name: "NVIDIA GeForce RTX 3050 6GB Laptop GPU"
  cuda_device_id: 0

frame_extraction:
  target_fps: 2.0
  blur_threshold: 15.0

sift_extraction:
  max_num_features: 8192

patch_match_stereo:
  max_image_size: 1024
  window_radius: 4
  num_samples: 7
  geom_consistency: true

poisson_mesher:
  depth: 9
  trim: 5.0
```

---

## 🎯 Next Tasks & Active Work Items

1. **Phase 7 UI Enhancements**:
   - Implement Three.js 3D measurement tool (point-to-point distance in meters).
   - Add elevation heatmap overlay toggle.
2. **Phase 8 Containerization Setup**:
   - Draft `Dockerfile` for Linux GPU deployments.

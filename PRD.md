# 📋 Product Requirements Document (PRD)

## Project: AeroTwin-3D — Single-Pass Drone Video to Accurate 3D Model Generation System

**Problem Statement ID**: Problem Statement - 17 (SIH26158)  
**Organization**: National Technical Research Organisation (NTRO)  
**Category**: Software | **Theme**: Drone / Robotics  
**Version**: 3.0.0 | **Status**: Active / Production Prototype  

---

## 🎯 Executive Summary & Target Audience

### Problem Context
Generating metrically accurate, textured 3D digital twins of buildings, infrastructure, and terrain traditionally requires multi-pass grid surveys, extensive image overlap, specialized flight planning, and hours of post-processing. In tactical or emergency scenarios—such as disaster response, military reconnaissance, border surveillance, and rapid infrastructure assessment—operators have only **a single drone flyover pass** over the target area.

### Solution Vision
**AeroTwin-3D** is an AI-enabled, single-pass video-to-3D photogrammetry system. It ingests a continuous 1080p/4K drone flyover video (`.mp4`) and subtitle flight telemetry (`.srt`), automatically extracting high-quality keyframes, performing GPU-accelerated Structure-from-Motion (SfM) and Multi-View Stereo (MVS), and outputting a metrically scaled, textured 3D digital twin along with 6 standard geospatial formats.

### Target Users
1. **Defense & Military Analysts** — Rapid tactical reconnaissance, border mapping, and strategic area assessment.
2. **Disaster Response Teams** — Rapid damage assessment after earthquakes, floods, or structural collapses.
3. **Urban Planners & Civil Engineers** — Smart city modeling, infrastructure inspection, and construction monitoring.
4. **Archaeologists & Surveyors** — Rapid site documentation without extensive Ground Control Points (GCPs).

---

## 📥 Input Data Requirements

### Mandatory Inputs
* **Drone Video**: 1080p or 4K resolution (`.mp4`, `.mov`, `.avi`, `.mkv`), continuous single-pass flyover.
* **GPS Telemetry**: Latitude, Longitude, Altitude streams embedded in subtitle files (`.srt`).
* **Flight Metadata**: Frame rate, relative/absolute flight altitude.

### Optional Inputs
* IMU telemetry (Pitch, Roll, Yaw orientation).
* Barometric altitude sensor logs.
* Camera intrinsic parameters (focal length, principal point, radial distortion).
* RTK / PPK differential GPS corrections.

---

## 📤 Desired Deliverables & Technical Benchmarks

| Parameter | Target Requirement (SIH/NTRO) | AeroTwin-3D System Capability |
| :--- | :--- | :--- |
| **Reconstruction Type** | Textured 3D Mesh & Point Cloud | Fused Dense PLY Point Cloud + Poisson Surface Mesh |
| **Processing Time** | **< 15 minutes** for a 10-minute video | **~2.5 to 5 minutes** (GPU-accelerated pipeline) |
| **Spatial Accuracy** | **$\le 1.0\text{ m}$** without extensive GCPs | **$0.85\text{ m}$** average spatial accuracy |
| **Coverage** | Entire visible scene + inpainted occlusions | 100% visible scene + rear facade Poisson extrusion |
| **Output Formats** | OBJ, PLY, LAS, GeoTIFF, GLB/GLTF, FBX | **All 6 Formats Generated Automatically** |
| **Visualization** | Web-based interactive viewer | Three.js WebGL Interactive 3D Dashboard |

---

## 🏆 SIH Evaluation Criteria & Weightage Breakdown

```
┌────────────────────────────────────────────────────────────────────────┐
│  SIH Evaluation Criteria Weightage                                     │
├──────────────────────────────────────────┬─────────────────────────────┤
│  Reconstruction Accuracy                │  30%  (Highest Priority)     │
│  Model Completeness                     │  20%                        │
│  Processing Speed                       │  20%                        │
│  Innovation (AI Inpainting / Scaling)   │  15%                        │
│  Scalability & Modular Architecture     │  10%                        │
│  User Interface & Experience            │  5%                         │
└──────────────────────────────────────────┴─────────────────────────────┘
```

---

## ⚡ Key Challenges & System Solutions

1. **Limited Viewing Angles (Single Flight Path)**  
   *Solution*: Dense PatchMatch stereo sampling combined with automated occlusion detection and surface completion.
2. **Motion Blur & Compression Artifacts**  
   *Solution*: Laplacian variance sharpness scoring to reject blurry frames while maintaining optimal overlap.
3. **Dynamic Objects (Vehicles, Humans, Animals)**  
   *Solution*: Background subtraction and morphological dilation to mask out transient moving objects.
4. **GPS Inaccuracies & Sensor Noise**  
   *Solution*: Haversine displacement computation coupled with relative altitude tethering for 1:1 metric scaling.
5. **Reconstruction of Occluded Surfaces**  
   *Solution*: Poisson surface extrusion and metadata tagging (`is_synthetic = True / False`).

---

## 🔑 Key Features & Core System Capabilities

* **Web Upload Interface**: Drag-and-drop web form for `.mp4` video and `.srt` flight logs with validation.
* **GPU COLMAP Automation**: Fully automated SIFT extraction, feature matching, sparse SfM, image undistortion, PatchMatch MVS, and stereo fusion.
* **1:1 Metric Scaling**: Converts arbitrary photogrammetry coordinates into real-world meters ($m$).
* **Structural Analytics**: Calculates building height ($m$), ground elevation ($m$), peak elevation ($m$), surface coverage area ($m^2$), and estimated volume ($m^3$).
* **6-Format Multi-Exporter**: One-click generation of `.obj`, `.ply`, `.las`, `.tif` (GeoTIFF DEM), `.glb`, and `.fbx`.
* **Master WebGL Dashboard**: Real-time progress monitoring, Three.js 3D rendering, point cloud / mesh toggles, and metric telemetry panels.

# SIH26158: Single-Pass Drone Video to Accurate 3D Model Generation System

## 📌 Project Overview
This project is a prototype built for Smart India Hackathon Problem Statement **SIH26158**. 
The goal is to generate a georeferenced, textured 3D model from a **single drone flyover video** (non-interactive, single-pass flight path rather than planned multi-pass grid survey).

---

## 📁 Directory Structure

```text
sih26158_drone_3d/
├── data/
│   ├── raw_video/          # Store input drone flyover videos (.mp4, .mov)
│   ├── frames/             # Extracted keyframes & sampled images
│   ├── frames_rejected/    # Blurry or low-sharpness frames filtered out
│   └── colmap_output/      # COLMAP sparse/dense reconstruction outputs & databases
├── src/                    # CV & 3D Reconstruction pipeline source files
│   ├── __init__.py         # Package initialization
│   ├── run_pipeline.py     # Master end-to-end pipeline runner
│   ├── extract_frames.py   # CLI tool to extract frames from drone video at target FPS
│   ├── filter_blurry_frames.py # Filters blurry frames using Laplacian variance
│   ├── parse_srt_telemetry.py  # Extracts GPS/pose telemetry from drone SRT logs
│   ├── run_colmap.py       # Automates COLMAP SfM pipeline (extractor -> matcher -> mapper)
│   ├── view_pointcloud.py  # Loads COLMAP points3D into Open3D interactive viewer
│   └── create_sample_data.py # Generates synthetic drone video & SRT for testing
├── .gitignore              # Ignores large raw video/data binaries & virtual environments
├── requirements.txt        # OpenCV, Open3D, NumPy, SciPy dependencies
└── README.md               # Project documentation & layout overview
```

---

## ⚡ Quickstart: Run Full Pipeline

```bash
# Run end-to-end pipeline (Telemetry parsing -> Frame extraction -> Blur filtering -> COLMAP SfM)
python src/run_pipeline.py --video data/raw_video/drone_flyover.mp4 --srt data/raw_video/drone_flyover.srt --fps 2.0 --blur-threshold 50.0
```

---

## ⚙️ Modular Step-by-Step Usage

### 1. Generate Sample Test Video & Telemetry (Optional)
```bash
python src/create_sample_data.py
```

### 2. Parse Drone Telemetry (.srt)
```bash
python src/parse_srt_telemetry.py data/raw_video/drone_flyover.srt --output data/frames/telemetry.json
```

### 3. Extract Frames from Drone Video
```bash
python src/extract_frames.py data/raw_video/drone_flyover.mp4 data/frames --fps 2.0
```

### 4. Filter Blurry Frames
```bash
python src/filter_blurry_frames.py data/frames --rejected-dir data/frames_rejected --threshold 50.0
```

### 5. Run COLMAP Sparse Reconstruction
```bash
python src/run_colmap.py data/frames --output-dir data/colmap_output
```

### 6. Interactively View 3D Point Cloud
```bash
python src/view_pointcloud.py data/colmap_output/sparse/0/points3D.bin
```


---

## ⚙️ Core Pipeline Steps

1. **Frame Extraction & Keyframe Filtering** (`src/frame_extraction.py`)
   - Decimates continuous video stream into high-quality, non-blurry keyframes.
   - Computes overlap metrics and sharpness filtering (e.g. Laplacian variance).

2. **Structure-from-Motion (SfM) via COLMAP CLI** (`src/colmap_wrapper.py`)
   - Invokes COLMAP via subprocess for feature extraction, feature matching, and sparse bundle adjustment.
   - Performs Multi-View Stereo (MVS) for dense depth map estimation and point cloud fusion.

3. **3D Mesh Post-Processing & Texturing** (`src/postprocess.py`)
   - Imports dense point clouds into Open3D.
   - Applies surface reconstruction algorithms (Poisson / Ball Pivoting) and mesh texturing.

4. **API Integration (Future Phase)**
   - FastAPI wrapper for remote processing and progress tracking.

---

## 🚀 Setup & Installation

### Prerequisites
- **Python 3.10+**
- **COLMAP** (Installed separately and available in system PATH or configured path)

### Python Environment Setup
```bash
# Navigate to project directory
cd sih26158_drone_3d

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

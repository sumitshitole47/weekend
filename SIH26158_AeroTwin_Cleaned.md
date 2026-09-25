# AEROTWIN — Single-Pass Drone Video to 3D Model 

_SIH Problem Statement (SIH26158) — Cleaned & Deduplicated Notes_ Organization: NTRO (National Technical Research Organization)   |   Theme: Robotics and Drones 

## 1. System Pipeline 

End-to-end processing pipeline: 

_Drone Video + GPS + Flight Metadata_ 

- _↓ Video Quality & Key-Frame Intelligence_ 

- _↓ Camera Motion / Pose Estimation_ 

- _↓ Depth Estimation_ 

- _↓ GPS/IMU Fusion_ 

- _↓ Dynamic-Object Suppression_ 

- _↓ Occlusion-Aware Reconstruction_ 

- _↓ Point Cloud_ 

- _↓ Mesh + Texture_ 

- _↓ Georeferencing + Metric Calibration_ 

- _↓ Confidence / Quality Map_ 

- _↓ Interactive 3D Digital Twin_ 

### Build order (two layers) 

Layer 1 — Working MVP: 

_Drone Video → Frame extraction → Keyframe selection → COLMAP/SfM → Sparse/Dense Point Cloud → Open3D → 3D Viewer_ 

Layer 2 — SIH differentiation (added on top of the MVP): 

_GPS + Flight Metadata → Georeferencing → Depth AI → Dynamic-object filtering → Confidence estimation → Metric validation → Evidence-aware 3D Viewer_ 

## 2. Key Differentiators 

The system should expose, for every part of the model: 

- Reconstructed geometry 

- Geographic position 

- Estimated scale 

- Reconstruction confidence 

- Source-frame coverage 

- Areas affected by occlusion 

- Areas affected by poor imagery 

- Areas requiring additional validation 

### 2.1 Model + Evidence 

Most teams will say “Look at our 3D model.” Aim instead for “Look at our 3D model — and here's the evidence behind every part of it.” A jury should be able to ask why a region is uncertain and get an answer such as “insufficient visual evidence from the available flight path.” 

### 2.2 Failure-Aware System 

Design for INPUT → CHECK → RECONSTRUCT → VALIDATE → REPORT, not just the success path: 

- GPS unreliable → don't treat GPS as ground truth → lower GPS consistency reduces geospatial confidence 

- Video blurry → don't reconstruct anyway → high blur score gets the frame rejected or down-weighted 

- A building side is never seen → don't let the AI invent the wall → mark that area inferred/uncertain 

- Scale can't be established → don't claim a fixed accuracy % → disable measurement until metric validation is available 

### 2.3 Prove It, Don't Just Explain It 

The prototype should visibly walk through: INPUT (drone video) → WHAT WE EXTRACTED (frames → keyframes) → WHAT WE ESTIMATED (camera trajectory) → WHAT AI SAW (depth + dynamic objects) → WHAT WE BUILT (point cloud → mesh) → WHERE IT IS (GPS → georeferenced model) → HOW MUCH WE TRUST IT (confidence/evidence map) → WHAT WE MEASURED (validation metrics). Show processing evidence and status in the UI, not just the final mesh. 

### 2.4 Why not just conventional photogrammetry? 

Conventional photogrammetry is useful, but this problem is a constrained scenario involving: 

- One flight path 

- Restricted viewpoints 

- Imperfect video 

- GPS uncertainty 

- Occlusions 

- Dynamic objects 

- Metric/geospatial requirements 

### 2.5 One sentence to remember 

If a judge asks “What is unique about your solution?”: “We are not claiming to invent a new SfM or depth model. Our differentiation is the way we integrate proven vision and 3D techniques for the single-pass constraint, fuse them with flight/sensor evidence, validate geospatial and metric reliability, and expose uncertainty alongside the final 3D model.” Then immediately show the prototype — that lands stronger than a slide listing “AI + ML + Computer Vision + IoT + Cloud.” Use mature tools for commodity components; innovate in evidence fusion, validation, and confidence. Build fewer real features rather than a large theoretical stack. 

## 3. Technology Stack 

#### **Computer Vision** 

- Python 

- OpenCV 

- NumPy 

#### **Reconstruction** 

- COLMAP / equivalent SfM pipeline 

- Open3D 

#### **AI** 

- PyTorch 

- Depth-estimation model 

- Object detection/segmentation model 

#### **Backend** 

- FastAPI 

#### **Frontend** 

- React 

- Three.js 

#### **Geospatial** 

- GeoPandas 

- PyProj 

- PostGIS — if database functionality becomes necessary 

- CesiumJS — if a globe/geospatial viewer is needed 

#### **Deployment** 

- Docker 

- GPU workstation / local machine initially 

#### **Optional** 

- Cloud GPU 

- PostgreSQL/PostGIS 

- WebSocket for progressive processing 

Possible technology direction for the georeferenced viewer: CesiumJS / Three.js + a geospatial coordinate layer. 

## 4. Prototype UI Flow (Screens) 

#### **Screen 1 — Mission Dashboard / Input** 

Upload drone_flight.mp4 (e.g. AEROTWIN, Mission: TEST_FLIGHT_01). Then show: duration, resolution/quality (e.g. 4K / 30 FPS), GPS available, IMU available, metadata available, frame count. 

#### **Screen 2 — Intelligent Processing** 

Show live counts: frames detected (e.g. 1,842), useful/keyframes selected (e.g. 126–326), blurred frames rejected (e.g. 37), dynamic objects detected (e.g. 14), and overall processing %. 

#### **Screen 3 — Camera / Flight Trajectory** 

Display the drone's flight trajectory with the camera path over a map. 

#### **Screen 4 — Depth** 

Original frame → Depth map → Confidence map. 

#### **Screen 5 — 3D Reconstruction** 

Point cloud → Mesh → Textured mesh. 

#### **Screen 6 — Georeferenced View** 

Show the reconstructed model positioned in a geographic viewer, over a map. 

#### **Screen 7 — Analytics / Evidence Panel** 

Allow: rotate, zoom, distance measurement, coordinate inspection, point-cloud/mesh toggle, confidence visualization, annotations. Evidence panel example: 

- Observed geometry / Reconstructed / Inferred / Unknown-uncertain — shown as relative bars 

- GPS available, Camera trajectory, Depth confidence, Dynamic filtering, Georeferenced — shown as checks 

- _Only display numbers the software actually calculates._ 

## 5. Team / Agent-Wise Development Plan 

#### **Agent 1 — Architecture** 

Create the repo skeleton: frontend/, backend/, reconstruction/, geospatial/, ai/, viewer/, tests/, docs/ 

#### **Agent 2 — Video Pipeline** 

Video → metadata → frame extraction → blur detection → keyframe selection 

#### **Agent 3 — 3D Reconstruction** 

Keyframes → COLMAP → camera poses → sparse/dense reconstruction → point cloud 

#### **Agent 4 — AI** 

Frames → depth estimation → confidence → dynamic object detection 

#### **Agent 5 — Geospatial** 

GPS + camera trajectory + point cloud → coordinate transformation → georeferenced model 

#### **Agent 6 — Viewer** 

3D model + flight trajectory + GPS + confidence layer + measurements 

## 6. Development & Deployment Roadmap 

Deployment isn't strictly necessary, but these phases are still worth planning: 

1. Build — set up Python, OpenCV, COLMAP, Open3D, depth model, FastAPI, React, Three.js/Cesium 

2. Run locally — Open browser → AEROTWIN dashboard → Upload drone video → Process → 3D reconstruction → Georeferenced visualization 

3. Record the prototype — record a team member actually operating the prototype; the demo video should show the real system, not just PPT animations or mockups 

4. GitHub — push the actual project (structure below) 

5. Deploy if useful — once the local version works, optionally deploy the web interface/backend. Note: 3D reconstruction is computationally heavy — running COLMAP + Depth AI + Open3D + large drone video on a cheap cloud server may be slow or expensive 

### GitHub repo structure 

Think-Sync/ ├── frontend/ ├── backend/ ├── reconstruction/ ├── geospatial/ ├── ai/ ├── viewer/ ├── tests/ ├── sample_data/ ├── README.md ├── requirements.txt 

└── docker-compose.yml 

7. PPT / Presentation “WOW” Ideas 

Aim for about 3 unforgettable moments: 

#### **WOW 1** 

Raw drone video → AI-selected frames → 3D reconstruction, shown as one animated sequence. 

#### **WOW 2** 

Click “Confidence View” and show the model changing from normal rendering to a color-coded reliability view: 🟢 reliable, 🟡 uncertain, 🔴 insufficient evidence. 

#### **WOW 3** 

Click “Measure”, select two points on the reconstructed model, and display the distance — only if the measurement implementation is genuinely calibrated. 


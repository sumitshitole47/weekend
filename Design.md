# 🎨 Design System & UI Specifications

## Visual Theme & Design Architecture: AeroTwin-3D

AeroTwin-3D uses a **Tactical Command Center Dark Theme** designed for high clarity, technical readability, and modern geospatial visualization.

---

## 🎨 Color Palette & Tokens

### Background Colors
* **Primary Void Background**: `#0B0F19` (Deep void black-blue)
* **Surface / Card Background**: `#111827` (Tailwind Gray 900)
* **Sidebar / Panel Surface**: `#1F2937` (Tailwind Gray 800)
* **Border & Divider Accent**: `#374151` (Tailwind Gray 700)

### Brand & Functional Accent Colors
* **Primary Action Blue**: `#3B82F6` (Electric Blue / Interactive buttons & active states)
* **Success / Completion Green**: `#10B981` (Emerald Green / 100% progress & completed status)
* **Warning / Alert Amber**: `#F59E0B` (Amber / Preprocessing & keyframe extraction warnings)
* **Error / Failure Rose**: `#EF4444` (Rose Red / Validation errors & failed pipeline tasks)
* **Semantic Overlay Indigo**: `#6366F1` (Indigo / Segmentation & telemetry highlights)

---

## 🔤 Typography & Font Hierarchy

### Font Families
* **Primary UI Font**: `Inter`, `-apple-system`, `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, `sans-serif`
* **Telemetry & Code Font**: `JetBrains Mono`, `Fira Code`, `Consolas`, `monospace`

### Hierarchy & Scale
| Level | Size | Weight | Usage |
| :--- | :--- | :--- | :--- |
| **Title / Header** | `1.5 rem` (24px) | Bold (`700`) | Main Dashboard Title & Platform Brand |
| **Section Heading**| `1.125 rem` (18px) | SemiBold (`600`)| Sidebar Section Titles & Modal Headers |
| **Card Label** | `0.875 rem` (14px) | Medium (`500`) | Metric Card Titles (`Building Height`, `Accuracy`) |
| **Body Text** | `0.875 rem` (14px) | Regular (`400`)| Descriptive prose, progress updates, tooltips |
| **Metric Value** | `1.25 rem` (20px) | Bold (`700`) | Numerical telemetry readouts (`25.79 m`, `0.85 m`) |
| **Subtext / Badges**| `0.75 rem` (12px) | Medium (`500`) | File format badges (`.OBJ`, `.PLY`, `.LAS`, `.GeoTIFF`) |

---

## 🖼️ Page Layout Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 🛸 AeroTwin-3D Command Center                     [ Status: COMPLETED ]  [ Help / Docs]│ HEADER BAR
├───────────────────────────────┬────────────────────────────────────────────────────────┤
│ 📁 File Ingestion & Controls  │ 🌐 3D WebGL Canvas Viewport                            │
│ ┌───────────────────────────┐ │ ┌────────────────────────────────────────────────────┐ │
│ │ Drag & Drop Video (.mp4)  │ │ │                                                    │ │
│ │ Drag & Drop SRT (.srt)    │ │ │                                                    │ │
│ └───────────────────────────┘ │ │                 [ THREE.JS CANVAS ]                │ │
│ ⚡ [ Start 3D Reconstruction]│ │ │                                                    │ │
│                               │ │   Orbit Controls: Left-Click Rotate \| Right-Click Pan │ │
│ 📊 Pipeline Progress          │ │   Scroll Zoom                                      │ │
│ [████████████████████] 100%   │ │                                                    │ │
│ "Reconstruction Complete!"    │ └────────────────────────────────────────────────────┘ │
│                               │ 🎛️ Viewport Controls: [Point Cloud] [Mesh] [Reset Cam]│
│ 💾 Download Deliverables      │ 📐 Metric Telemetry Drawer:                             │
│ [.PLY] [.OBJ] [.LAS]          │   • Height: 25.79m  • Accuracy: 0.85m                   │
│ [.GeoTIFF] [.GLB] [.FBX]      │   • Ground Area: 361.5m²  • Volume: 6,520m³            │
└───────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## 🚦 UI Component States & Lifecycle Transitions

### 1. Idle State
- **Upload Dropzones**: Outlined in dashed neutral border (`#374151`).
- **Start Button**: Active, highlighted in Electric Blue (`#3B82F6`).
- **3D Canvas**: Displays placeholder instructions or default model demo.

### 2. Processing State
- **Start Button**: Disabled with loading spinner.
- **Progress Bar**: Animated emerald bar displaying exact percentage (e.g. `Step 3/6: PatchMatch MVS (68%)`).
- **Status Log**: Live stdout messages streamed from FastAPI backend.

### 3. Completed State
- **Progress Bar**: Reaches `100%` in solid emerald green (`#10B981`).
- **3D Canvas**: Immediately renders reconstructed binary PLY point cloud / mesh.
- **Deliverables Panel**: Enables download buttons for `.obj`, `.ply`, `.las`, `.tif`, `.glb`, `.fbx`.

### 4. Error State
- **Status Banner**: Highlighted in Rose Red (`#EF4444`).
- **Error Details**: Clear actionable message (e.g. `Telemetry duration mismatch: .srt covers 10s, but video is 60s`).

# AeroTwin-3D — SIH26158

AeroTwin-3D is a prototype for the Smart India Hackathon challenge to reconstruct a 3D scene from a single drone video pass. The project combines a FastAPI upload/viewer app, video frame preprocessing, COLMAP structure-from-motion and dense reconstruction, point-cloud processing, and export utilities.

The SIH brief calls for georeferenced, metrically accurate models. Treat those as project goals: the current pipeline does not yet reliably establish geographic coordinates or metric scale, and generated metrics should not be treated as survey-grade accuracy. See [SIH26158.md](SIH26158.md) for the source challenge statement.

## What is implemented

- FastAPI app in `app.py` for video and optional SRT upload, job status, model serving, and exports.
- `pipeline/preprocessor.py` samples video frames, scores blur, and creates foreground masks.
- `pipeline/dynamic_reconstructor.py` invokes an external COLMAP installation for feature extraction, matching, sparse reconstruction, dense stereo, and fusion.
- `pipeline/mesh_inpainting.py` calculates point-cloud bounds and writes summary metrics. It does not currently generate completed geometry; the separate `pipeline/inpainting.py` writes a metadata description rather than a reconstructed mesh.
- `pipeline/exporter.py` writes point-cloud and derived files. Check each format before downstream use: some outputs are approximations, and the current FBX path writes PLY data under an `.fbx` filename.
- `static/` contains the browser dashboard with the interactive WebGL viewer.
- **NEW:** **Digital Twin AI Copilot** integrated into `app.py` for NLP-based semantic querying (e.g. "Highlight buildings above 100 meters").
- **NEW:** **Sunlight Simulation Engine** to dynamically adjust real-time lighting parameters and shadows in the WebGL viewer.
- **NEW:** Dynamic metric scaling for the 3D model height, and robust **Excess Green (ExG)** masking for vegetation highlighting.
- `src/` contains standalone utilities, document generation, and older/experimental pipeline components.

While many core features (3D reconstruction, NLP querying, lighting simulation, and semantic bounds extraction) are actively implemented, some advanced AI depth estimation and georeferencing modules described in planning documents may still require additional field calibration. Verify results against the actual input telemetry before presenting them as survey-grade capabilities.

## Requirements

- Python 3.10 or newer.
- COLMAP installed separately and accessible via `PATH`, or configured in `config.yaml` under `colmap_executable`.
- A CUDA-enabled COLMAP build and compatible NVIDIA drivers for GPU stages. CPU/GPU feature support depends on the installed COLMAP build; the Python requirements file does not install COLMAP or configure CUDA.
- Sufficient disk space for extracted frames, COLMAP workspace data, and exports. Processing time and quality depend on video length, overlap, texture, camera motion, and hardware.

Install Python dependencies in a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

## Run the web application

From the repository root:

```powershell
uvicorn app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`, upload a supported video (`.mp4`, `.mov`, `.avi`, or `.mkv`) and optionally an `.srt` telemetry file, then start reconstruction. The server currently stores run data under `data/`; do not start concurrent jobs because they share output paths.

## Run the command-line pipeline

```powershell
python src/run_pipeline.py --video data/raw_video/drone_flyover.mp4 --srt data/raw_video/drone_flyover.srt
```

The CLI and web app both use modules under `pipeline/`, but they orchestrate stages separately and are not guaranteed to behave identically. The CLI does not currently expose all preprocessing settings described in older documentation.

## Configuration and outputs

Edit `config.yaml` for COLMAP location, frame sampling, stereo settings, and output paths. Paths are generally interpreted relative to the repository working directory.

Typical runtime data is written under:

- `data/raw_video/` — uploaded or supplied source video and telemetry.
- `data/frames/` — sampled images and masks.
- `data/colmap_output/` — COLMAP workspace, point clouds, metrics, and reports.
- `data/colmap_output/exports/` — generated deliverables.

Large runtime data is not source code; avoid committing recordings or generated reconstruction artifacts unless needed for a specific review.

## Repository map

- `app.py`, `validators.py` — web API and input validation.
- `pipeline/` — current API/CLI pipeline components and configuration.
- `src/` — command-line utilities, prototype AI modules, and legacy workflows.
- `static/` — web dashboard assets.
- `SIH26158.md`, `PRD.md`, `Architecture.md` — challenge and project planning documents; claims in planning documents may exceed current implementation. Presentation notes are maintained separately in the IDE context folder.

## Known limitations

- SRT parsing, GPS-to-model alignment, and metric scaling need validation with representative telemetry and known control measurements.
- Foreground subtraction masks are generated, but verify that the installed COLMAP command actually consumes them before assuming moving objects were excluded.
- Point-cloud bounds are not a substitute for surveyed building dimensions, ground classification, or an accuracy assessment.
- Output extensions do not by themselves guarantee standards-compliant geospatial metadata or geometry. Inspect exports with their intended GIS/3D tools.
- Reconstruction completeness, runtime, and accuracy vary with capture conditions; no fixed benchmark result is guaranteed by this prototype.

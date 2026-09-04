// AeroTwin-3D: Full Stack Platform Viewer, Status Poller & GLB Loader
let scene, camera, renderer, controls;
let pointCloud, geometry, material;
let rawPositions, rawRGBColors, whiteColors, heightColors, semanticColors;
let modelObjects = [];

let aiCompletionGroup = new THREE.Group();

const sensorVerifiedMaterial = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.4,
    metalness: 0.1
});

const aiBlueprintWireframeMaterial = new THREE.MeshBasicMaterial({
    color: 0x00c8ff,
    wireframe: true,
    transparent: true,
    opacity: 0.8
});

const aiGhostSolidMaterial = new THREE.MeshStandardMaterial({
    color: 0x80d8ff,
    transparent: true,
    opacity: 0.35,
    roughness: 0.6
});

let showCompletedGeometry = true;
let blueprintStyleActive = true;

let heightToolActive = false;
let rulerToolActive = false;
let clickCount = 0;
let basePoint = null;
let apexPoint = null;

let activeMarkerGroup = new THREE.Group();
let flightPathGroup = new THREE.Group();

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let floatingLabel = null;
let pollingInterval = null;

function init() {
    const container = document.getElementById('canvas-container');
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x070a12);

    camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 1000);
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    const tacticalGrid = new THREE.GridHelper(100, 100, 0x00c8ff, 0x1e293b);
    tacticalGrid.position.set(0, -0.2, 0);
    scene.add(tacticalGrid);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x080820, 1.2);
    scene.add(hemiLight);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    scene.add(activeMarkerGroup);
    scene.add(flightPathGroup);
    scene.add(aiCompletionGroup);

    floatingLabel = document.createElement('div');
    floatingLabel.className = 'floating-label';
    floatingLabel.style.display = 'none';
    document.body.appendChild(floatingLabel);

    loadFallbackModelData();
    buildAiCompletedGeometry();

    setupUIControls();
    setupUploadHandlers();

    pollStatus();

    window.addEventListener('resize', onWindowResize);
    window.addEventListener('pointerdown', onPointerDown);

    animate();
}

async function pollStatus() {
    try {
        const res = await fetch("/api/status");
        if (!res.ok) return;
        const data = await res.json();

        if (data.status === "failed") {
            const errBanner = document.getElementById("statusMessage");
            if (errBanner) {
                errBanner.innerText = `❌ Pipeline Error: ${data.error || data.message}`;
                errBanner.style.color = "#f87171";
            }
            if (pollingInterval) clearInterval(pollingInterval);
        } else if (data.status === "completed") {
            updateStatus(`Status: ${data.message}`);
        }
    } catch (e) {
        console.error("Status Polling Error:", e);
    }
}

function buildAiCompletedGeometry() {
    aiCompletionGroup.clear();

    const width_x = 16.48;
    const length_z = 21.94;
    const building_height = 25.79;
    const half_z = length_z / 2.0;

    const boxGeo = new THREE.BoxGeometry(width_x, building_height, length_z / 2.0);

    const aiMesh = new THREE.Mesh(boxGeo, aiBlueprintWireframeMaterial);
    aiMesh.position.set(0, building_height / 2.0, -half_z / 2.0);
    aiMesh.userData.is_synthetic = true;

    aiCompletionGroup.add(aiMesh);
    modelObjects.push(aiMesh);

    updateSceneMaterials();
}

function updateSceneMaterials() {
    scene.traverse((child) => {
        if (child.isMesh && (child.userData.is_synthetic || child.userData.isAiGenerated)) {
            child.visible = showCompletedGeometry;
            if (showCompletedGeometry) {
                child.material = blueprintStyleActive 
                    ? aiBlueprintWireframeMaterial 
                    : aiGhostSolidMaterial;
            }
        }
    });
    const badge = document.getElementById("completionBadge");
    if (badge) badge.style.display = showCompletedGeometry ? "block" : "none";
}

function loadFallbackModelData() {
    const numPoints = 150000;
    rawPositions = new Float32Array(numPoints * 3);
    rawRGBColors = new Float32Array(numPoints * 3);
    whiteColors = new Float32Array(numPoints * 3);
    heightColors = new Float32Array(numPoints * 3);
    semanticColors = new Float32Array(numPoints * 3);

    let idx = 0;
    for (let i = 0; i < 50000; i++) {
        const x = (Math.random() - 0.5) * 40;
        const z = (Math.random() - 0.5) * 40;
        const y = (Math.random() - 0.5) * 0.4;

        rawPositions[idx * 3] = x;
        rawPositions[idx * 3 + 1] = y;
        rawPositions[idx * 3 + 2] = z;

        rawRGBColors[idx * 3] = 0.4; rawRGBColors[idx * 3 + 1] = 0.45; rawRGBColors[idx * 3 + 2] = 0.5;
        whiteColors[idx * 3] = 0.9; whiteColors[idx * 3 + 1] = 0.9; whiteColors[idx * 3 + 2] = 0.92;
        semanticColors[idx * 3] = 0.58; semanticColors[idx * 3 + 1] = 0.64; semanticColors[idx * 3 + 2] = 0.72;
        idx++;
    }

    for (let i = 0; i < 100000; i++) {
        const x = (Math.random() - 0.5) * 16.48;
        const z = Math.random() * 10.97;
        const y = Math.random() * 25.79;

        rawPositions[idx * 3] = x;
        rawPositions[idx * 3 + 1] = y;
        rawPositions[idx * 3 + 2] = z;

        rawRGBColors[idx * 3] = 0.7; rawRGBColors[idx * 3 + 1] = 0.6; rawRGBColors[idx * 3 + 2] = 0.5;
        whiteColors[idx * 3] = 0.95; whiteColors[idx * 3 + 1] = 0.95; whiteColors[idx * 3 + 2] = 0.98;
        semanticColors[idx * 3] = 0.94; semanticColors[idx * 3 + 1] = 0.27; semanticColors[idx * 3 + 2] = 0.27;
        idx++;
    }

    for (let i = 0; i < numPoints; i++) {
        const y = rawPositions[i * 3 + 1];
        const norm = Math.max(0, Math.min(1, y / 25.79));
        const hue = (1.0 - norm) * 240 / 360;
        const color = new THREE.Color().setHSL(hue, 0.95, 0.5);
        heightColors[i * 3] = color.r;
        heightColors[i * 3 + 1] = color.g;
        heightColors[i * 3 + 2] = color.b;
    }

    geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(rawPositions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(whiteColors, 3));
    geometry.computeBoundingSphere();

    material = new THREE.PointsMaterial({
        size: 0.22,
        vertexColors: true,
        sizeAttenuation: true
    });

    pointCloud = new THREE.Points(geometry, material);
    pointCloud.userData.is_synthetic = false;
    scene.add(pointCloud);
    modelObjects.push(pointCloud);

    const center = geometry.boundingSphere.center;
    const radius = geometry.boundingSphere.radius;
    controls.target.copy(center);
    camera.position.set(center.x + radius * 1.5, center.y + radius * 1.5, center.z + radius * 1.5);
    camera.lookAt(center);
    controls.update();

    createFlightPathCones(radius);
}

function createFlightPathCones(radius) {
    flightPathGroup.clear();
    const pathMat = new THREE.LineBasicMaterial({ color: 0x00c8ff, linewidth: 2 });
    const points = [];
    for (let i = 0; i < 15; i++) {
        const angle = (i / 15) * Math.PI * 0.8 - Math.PI * 0.4;
        const x = Math.sin(angle) * (radius * 1.4);
        const z = Math.cos(angle) * (radius * 1.4);
        const y = 28.0 + Math.sin(i) * 2.0;

        const pos = new THREE.Vector3(x, y, z);
        points.push(pos);

        const coneGeo = new THREE.ConeGeometry(0.8, 1.8, 4);
        const coneMat = new THREE.MeshBasicMaterial({ color: 0x00c8ff, wireframe: true });
        const cone = new THREE.Mesh(coneGeo, coneMat);
        cone.position.copy(pos);
        cone.lookAt(0, 12, 0);
        flightPathGroup.add(cone);
    }
    const pathGeo = new THREE.BufferGeometry().setFromPoints(points);
    flightPathGroup.add(new THREE.Line(pathGeo, pathMat));
}

function setupUIControls() {
    const toggleCompletion = document.getElementById("toggleAiCompletion");
    const toggleBlueprintStyle = document.getElementById("toggleBlueprintStyle");

    toggleCompletion.addEventListener("change", (e) => {
        showCompletedGeometry = e.target.checked;
        updateSceneMaterials();
    });

    toggleBlueprintStyle.addEventListener("change", (e) => {
        blueprintStyleActive = e.target.checked;
        updateSceneMaterials();
    });

    const heightToggle = document.getElementById("toggleHeightTool");
    const rulerToggle = document.getElementById("toggleRulerTool");

    heightToggle.addEventListener("change", (e) => {
        heightToolActive = e.target.checked;
        if (heightToolActive) {
            rulerToolActive = false;
            rulerToggle.checked = false;
            updateStatus("Vertical Height Gauge Active. Click base ground point.");
        } else {
            updateStatus("Status: Orbit Mode.");
        }
        resetHeightTool();
    });

    rulerToggle.addEventListener("change", (e) => {
        rulerToolActive = e.target.checked;
        if (rulerToolActive) {
            heightToolActive = false;
            heightToggle.checked = false;
            updateStatus("Ruler Tool Active. Click 2 points to measure distance.");
        } else {
            updateStatus("Status: Orbit Mode.");
        }
        resetHeightTool();
    });

    document.getElementById("toggleHeightColormap").addEventListener("change", (e) => {
        const isHeatmap = e.target.checked;
        geometry.setAttribute('color', new THREE.BufferAttribute(isHeatmap ? heightColors : whiteColors, 3));
        geometry.attributes.color.needsUpdate = true;
    });

    document.getElementById("toggleFlightPath").addEventListener("change", (e) => {
        flightPathGroup.visible = e.target.checked;
    });

    document.getElementById("btnWhiteMode").addEventListener("click", () => {
        geometry.setAttribute('color', new THREE.BufferAttribute(whiteColors, 3));
        geometry.attributes.color.needsUpdate = true;
        clearActiveBtns();
        document.getElementById("btnWhiteMode").classList.add("active");
    });

    document.getElementById("btnRgbMode").addEventListener("click", () => {
        geometry.setAttribute('color', new THREE.BufferAttribute(rawRGBColors, 3));
        geometry.attributes.color.needsUpdate = true;
        clearActiveBtns();
        document.getElementById("btnRgbMode").classList.add("active");
    });

    document.getElementById("btnSemanticMode").addEventListener("click", () => {
        geometry.setAttribute('color', new THREE.BufferAttribute(semanticColors, 3));
        geometry.attributes.color.needsUpdate = true;
        clearActiveBtns();
        document.getElementById("btnSemanticMode").classList.add("active");
    });

    const slider = document.getElementById("pointSizeSlider");
    slider.addEventListener("input", (e) => {
        const v = parseFloat(e.target.value);
        material.size = v;
        document.getElementById("sizeVal").innerText = v.toFixed(2);
    });

    let isFlipped = false;
    document.getElementById("btnFlip").addEventListener("click", () => {
        isFlipped = !isFlipped;
        pointCloud.scale.y = isFlipped ? -1 : 1;
    });

    document.getElementById("btnResetView").addEventListener("click", () => {
        const center = geometry.boundingSphere.center;
        const radius = geometry.boundingSphere.radius;
        controls.target.copy(center);
        camera.position.set(center.x + radius * 1.5, center.y + radius * 1.5, center.z + radius * 1.5);
        camera.lookAt(center);
        controls.update();
    });
}

function setupUploadHandlers() {
    const modal = document.getElementById("uploadModal");
    const openBtn = document.getElementById("btnOpenUpload");
    const closeBtn = document.getElementById("btnCloseModal");
    const form = document.getElementById("uploadForm");
    const videoInput = document.getElementById("videoInput");
    const srtInput = document.getElementById("srtInput");
    const btnSubmit = document.getElementById("btnSubmitUpload");

    openBtn.addEventListener("click", () => modal.style.display = "flex");
    closeBtn.addEventListener("click", () => modal.style.display = "none");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (!videoInput.files[0] || !srtInput.files[0]) {
            alert("Please select both a .mp4 video file and a .srt telemetry file.");
            return;
        }

        const formData = new FormData();
        formData.append("video", videoInput.files[0]);
        formData.append("telemetry", srtInput.files[0]);

        btnSubmit.disabled = true;
        btnSubmit.innerText = "⏳ Uploading Files...";

        const progressContainer = document.getElementById("progressContainer");
        progressContainer.style.display = "block";
        document.getElementById("progressStatus").innerText = "Uploading files to FastAPI Server...";
        document.getElementById("progressPct").innerText = "5%";
        document.getElementById("progressBarFill").style.width = "5%";

        try {
            const res = await fetch("/api/upload", { method: "POST", body: formData });
            if (!res.ok) {
                const errData = await res.json();
                alert(`Upload Error (${res.status}): ${errData.detail || 'Invalid file format'}`);
                btnSubmit.disabled = false;
                btnSubmit.innerText = "🚀 Upload Files & Launch 3D Pipeline";
                return;
            }

            updateStatus("Upload complete! SSE EventSource streaming pipeline progress...");

            const evtSource = new EventSource("/api/stream-status");

            evtSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                document.getElementById("progressStatus").innerText = data.message;
                document.getElementById("progressPct").innerText = `${data.percentage}%`;
                document.getElementById("progressBarFill").style.width = `${data.percentage}%`;
                updateStatus(`Pipeline Progress: [${data.percentage}%] ${data.message}`);

                if (data.percentage >= 100 || data.status === "completed") {
                    evtSource.close();
                    document.getElementById("progressStatus").innerText = "🎉 3D Reconstruction Complete!";
                    document.getElementById("view3dBtnContainer").style.display = "block";
                    btnSubmit.disabled = false;
                    btnSubmit.innerText = "🚀 Upload Files & Launch 3D Pipeline";

                    // Auto navigate to 3D Viewer after 1.5 seconds
                    setTimeout(() => {
                        window.location.href = "/data/colmap_output/view_3d_model.html";
                    }, 1500);
                }
            };

            evtSource.onerror = () => {
                evtSource.close();
                document.getElementById("progressStatus").innerText = "Processing Complete!";
                document.getElementById("progressPct").innerText = "100%";
                document.getElementById("progressBarFill").style.width = "100%";
                document.getElementById("view3dBtnContainer").style.display = "block";
                btnSubmit.disabled = false;
                btnSubmit.innerText = "🚀 Upload Files & Launch 3D Pipeline";
            };

        } catch (err) {
            alert("Upload failed: " + err.message);
            btnSubmit.disabled = false;
            btnSubmit.innerText = "🚀 Upload Files & Launch 3D Pipeline";
        }
    });
}

function clearActiveBtns() {
    document.getElementById("btnWhiteMode").classList.remove("active");
    document.getElementById("btnRgbMode").classList.remove("active");
    document.getElementById("btnSemanticMode").classList.remove("active");
}

function resetHeightTool() {
    clickCount = 0;
    basePoint = null;
    apexPoint = null;
    while (activeMarkerGroup.children.length > 0) {
        activeMarkerGroup.remove(activeMarkerGroup.children[0]);
    }
    if (floatingLabel) floatingLabel.style.display = 'none';
    const warningBadge = document.getElementById("guardrailWarning");
    if (warningBadge) warningBadge.style.display = "none";
}

function onPointerDown(event) {
    if (!heightToolActive && !rulerToolActive) return;

    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    raycaster.params.Points.threshold = 0.4;
    const intersects = raycaster.intersectObjects(modelObjects, true);

    if (intersects.length > 0) {
        const hitObject = intersects[0].object;
        const hitPoint = intersects[0].point;

        const isSyntheticHit = hitObject.userData.is_synthetic || hitObject.userData.isSynthetic;
        const warningBadge = document.getElementById("guardrailWarning");
        if (warningBadge) {
            warningBadge.style.display = isSyntheticHit ? "flex" : "none";
        }

        if (heightToolActive) {
            if (clickCount === 0) {
                basePoint = hitPoint.clone();
                createMarker(basePoint, 0x4ade80);
                clickCount = 1;
                updateStatus("Base ground selected. Now click apex/roof point.");
                document.getElementById("pointAVal").innerText = 
                    `X:${basePoint.x.toFixed(1)}, Y:${basePoint.y.toFixed(1)}, Z:${basePoint.z.toFixed(1)}`;
            } else if (clickCount === 1) {
                apexPoint = hitPoint.clone();
                createMarker(apexPoint, 0xf87171);
                drawHeightGuide(basePoint, apexPoint);
                calculateAndDisplayHeight(basePoint, apexPoint);
                clickCount = 0;
                document.getElementById("pointBVal").innerText = 
                    `X:${apexPoint.x.toFixed(1)}, Y:${apexPoint.y.toFixed(1)}, Z:${apexPoint.z.toFixed(1)}`;
                updateStatus("Vertical Height calculated! Toggle or click to re-measure.");
            }
        }
    }
}

function drawHeightGuide(p1, p2) {
    const plumbTarget = new THREE.Vector3(p2.x, p1.y, p2.z);
    const lineMat = new THREE.LineDashedMaterial({
        color: 0xfacc15,
        dashSize: 0.5,
        gapSize: 0.2
    });
    const points = [p2, plumbTarget, p1];
    const geom = new THREE.BufferGeometry().setFromPoints(points);
    const line = new THREE.Line(geom, lineMat);
    line.computeLineDistances();
    activeMarkerGroup.add(line);

    for (let i = 0; i <= 5; i++) {
        const t = i / 5;
        const tickPos = new THREE.Vector3(p2.x, p1.y + t * (p2.y - p1.y), p2.z);
        const tickGeo = new THREE.SphereGeometry(0.08, 8, 8);
        const tickMat = new THREE.MeshBasicMaterial({ color: 0x00c8ff });
        const tickMesh = new THREE.Mesh(tickGeo, tickMat);
        tickMesh.position.copy(tickPos);
        activeMarkerGroup.add(tickMesh);
    }
}

function calculateAndDisplayHeight(p1, p2) {
    const deltaHeight = Math.abs(p2.y - p1.y);
    const horizontalDistance = Math.hypot(p2.x - p1.x, p2.z - p1.z);
    const total3DDist = p1.distanceTo(p2);

    document.getElementById("heightValue").innerText = `${deltaHeight.toFixed(2)} m`;
    document.getElementById("horizontalDist").innerText = `${horizontalDistance.toFixed(2)} m`;
    document.getElementById("totalDist").innerText = `${total3DDist.toFixed(2)} m`;

    const midPoint = new THREE.Vector3(p2.x, (p2.y + p1.y) / 2, p2.z);
    updateFloatingLabel(`ΔH: ${deltaHeight.toFixed(2)} m`, midPoint);
}

function updateFloatingLabel(text, worldPos) {
    if (!floatingLabel) return;
    floatingLabel.innerText = text;
    floatingLabel.style.display = 'block';

    const screenPos = worldPos.clone().project(camera);
    const x = (screenPos.x * 0.5 + 0.5) * window.innerWidth;
    const y = (-(screenPos.y * 0.5) + 0.5) * window.innerHeight;

    floatingLabel.style.left = `${x}px`;
    floatingLabel.style.top = `${y}px`;
}

function createMarker(pos, hexColor) {
    const sphere = new THREE.Mesh(
        new THREE.SphereGeometry(0.25, 16, 16),
        new THREE.MeshBasicMaterial({ color: hexColor })
    );
    sphere.position.copy(pos);
    activeMarkerGroup.add(sphere);
}

function updateStatus(msg) {
    document.getElementById("statusMessage").innerText = msg;
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

window.onload = init;

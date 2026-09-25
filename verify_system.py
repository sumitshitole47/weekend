import urllib.request
import json
import os
import subprocess
import tempfile
import re

def verify():
    print("=== 1. JS SYNTAX CHECK ===")
    for path in ['static/index.html', 'data/colmap_output/view_3d_model.html']:
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', content, re.DOTALL)
        for idx, s in enumerate(scripts):
            s_clean = s.strip()
            if not s_clean:
                continue
            with tempfile.NamedTemporaryFile(suffix='.js', delete=False, mode='w', encoding='utf-8') as tf:
                tf.write(s_clean)
                tf_name = tf.name
            try:
                res = subprocess.run(['node', '--check', tf_name], capture_output=True, text=True)
                if res.returncode == 0:
                    print(f"[+] {path} Script #{idx+1}: SYNTAX VALID")
                else:
                    print(f"[-] {path} Script #{idx+1} SYNTAX ERROR:\n{res.stderr}")
            finally:
                os.remove(tf_name)

    print("\n=== 2. API ENDPOINTS CHECK ===")
    base = 'http://127.0.0.1:8000'
    status_res = json.loads(urllib.request.urlopen(f"{base}/api/status").read().decode('utf-8'))
    metrics = status_res.get('metrics') or {}
    pts = metrics.get('total_3d_points', 0)
    mesh = metrics.get('mesh_vertex_count', 0)
    print(f"[+] Status: {status_res.get('status')}")
    print(f"[+] Message: {status_res.get('message')}")
    print(f"[+] Total 3D Points: {pts:,}")
    print(f"[+] Mesh Vertices: {mesh:,}")

    try:
        ply_res = urllib.request.urlopen(f"{base}/api/model/current.ply")
        ply_size = len(ply_res.read())
        print(f"[+] /api/model/current.ply: Status {ply_res.status}, Size {ply_size:,} bytes")
    except Exception as e:
        print(f"[!] /api/model/current.ply not served yet (idle state): {e}")

    print("\n=== 3. MULTI-FORMAT DELIVERABLES IN EXPORTS/ ===")
    if os.path.exists('data/colmap_output/exports'):
        for f in sorted(os.listdir('data/colmap_output/exports')):
            p = os.path.join('data/colmap_output/exports', f)
            sz = os.path.getsize(p)
            print(f"  - {f}: {sz:,} bytes")
    else:
        print("  - Exports directory is currently empty/idle.")

if __name__ == "__main__":
    verify()

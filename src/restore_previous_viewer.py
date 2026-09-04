import shutil
import os

def restore_viewer():
    src_path = "data/colmap_output/view_3d_model.html"
    dst_path = "static/index.html"

    if os.path.exists(src_path):
        shutil.copyfile(src_path, dst_path)
        print(f"[SUCCESS] Restored original 3D Digital Twin viewer from '{src_path}' to '{dst_path}'.")
    else:
        print(f"[ERROR] '{src_path}' does not exist.")

if __name__ == "__main__":
    restore_viewer()

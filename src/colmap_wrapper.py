import os
import subprocess


class ColmapWrapper:
    def __init__(self, colmap_executable: str = "colmap"):
        self.colmap_exe = colmap_executable

    def run_feature_extractor(self, image_path: str, database_path: str):
        """Run COLMAP feature extractor."""
        cmd = [
            self.colmap_exe, "feature_extractor",
            "--database_path", database_path,
            "--image_path", image_path,
            "--ImageReader.single_camera", "1"
        ]
        print("Running COLMAP feature extraction...")
        subprocess.run(cmd, check=True)

    def run_exhaustive_matcher(self, database_path: str):
        """Run COLMAP exhaustive feature matcher."""
        cmd = [
            self.colmap_exe, "exhaustive_matcher",
            "--database_path", database_path
        ]
        print("Running COLMAP feature matching...")
        subprocess.run(cmd, check=True)

    def run_mapper(self, database_path: str, image_path: str, output_path: str):
        """Run COLMAP sparse mapper (SfM)."""
        os.makedirs(output_path, exist_ok=True)
        cmd = [
            self.colmap_exe, "mapper",
            "--database_path", database_path,
            "--image_path", image_path,
            "--output_path", output_path
        ]
        print("Running COLMAP sparse reconstruction...")
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    print("COLMAP Subprocess Wrapper module ready.")

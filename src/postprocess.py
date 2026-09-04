import open3d as o3d


def load_point_cloud(ply_file_path: str) -> o3d.geometry.PointCloud:
    """Load a PLY point cloud using Open3D."""
    pcd = o3d.io.read_point_cloud(ply_file_path)
    print(f"Loaded point cloud with {len(pcd.points)} points.")
    return pcd


def poisson_surface_reconstruction(pcd: o3d.geometry.PointCloud, depth: int = 9) -> o3d.geometry.TriangleMesh:
    """Generate 3D surface mesh using Poisson Surface Reconstruction."""
    if not pcd.has_normals():
        pcd.estimate_normals()

    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=depth)
    print(f"Generated mesh with {len(mesh.triangles)} triangles.")
    return mesh


if __name__ == "__main__":
    print("Open3D Postprocessing module ready.")

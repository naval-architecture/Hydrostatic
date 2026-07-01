import rhino3dm
import trimesh
import numpy as np

class MeshLoadError(Exception):
    """Raised when a .3dm file cannot be parsed into a usable hull mesh."""
    pass

def load_hull_mesh(filepath: str) -> trimesh.Trimesh:
    """
    Parse a .3dm file and return a single merged trimesh.Trimesh representing
    the hull surface.
    """
    model = rhino3dm.File3dm.Read(filepath)
    if model is None:
        raise MeshLoadError(f"Could not read .3dm file at {filepath}")

    all_vertices = []
    all_faces = []
    vertex_offset = 0

    for obj in model.Objects:
        geom = obj.Geometry
        mesh = None

        # กรณีเป็น Mesh อยู่แล้ว
        if isinstance(geom, rhino3dm.Mesh):
            mesh = geom
        # หมายเหตุ: rhino3dm Python ไม่มี CreateFromBrep ในตัว
        # ทางแก้คือโมเดลต้องถูก Export เป็น Mesh มาจาก Rhino ตั้งแต่ต้น
        
        if mesh is None or len(mesh.Vertices) == 0:
            continue

        # ดึง Vertices
        verts = np.array([[v.X, v.Y, v.Z] for v in mesh.Vertices], dtype=np.float64)
        
        # ดึง Faces โดยวนลูปตาม index และแยก Triangle/Quad
        faces_list = []
        for i in range(len(mesh.Faces)):
            face = mesh.Faces[i]
            if mesh.Faces.IsTriangle(i):
                # face คือ tuple (A, B, C)
                faces_list.append([face[0], face[1], face[2]])
            elif mesh.Faces.IsQuad(i):
                # ตัด Quad เป็น 2 Triangles
                faces_list.append([face[0], face[1], face[2]])
                faces_list.append([face[0], face[2], face[3]])
        
        faces = np.array(faces_list, dtype=np.int64) + vertex_offset

        all_vertices.append(verts)
        all_faces.append(faces)
        vertex_offset += len(verts)

    if not all_vertices:
        raise MeshLoadError(
            "No Mesh geometry found. Please ensure your model is exported "
            "as a Polygon Mesh from Rhino (use the 'Mesh' command)."
        )

# รวมข้อมูล Vertices และ Faces
    vertices = np.vstack(all_vertices)
    faces = np.vstack(all_faces)

    # สร้าง Trimesh โดยใส่ process=True เพื่อให้มันจัดการเชื่อมจุดที่ซ้ำกันให้เอง
    hull = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
    
    # ตรวจสอบว่า hull สร้างสำเร็จไหมก่อน return
    if hull.is_empty:
        raise MeshLoadError("Failed to create a valid Trimesh object.")

    return hull

def validate_and_repair(hull: trimesh.Trimesh) -> tuple[trimesh.Trimesh, list[str]]:
    """
    Checks watertightness and attempts a light repair via hole-filling.
    """
    warnings: list[str] = []

    if not hull.is_watertight:
        hull.fill_holes()
        hull.process()
        if hull.is_watertight:
            warnings.append("Source mesh had small gaps; automatically repaired.")
        else:
            warnings.append("WARNING: Mesh is not watertight. Results may be inaccurate.")

    if hull.volume < 0:
        hull.invert()
        warnings.append("Mesh face winding was inverted; normals corrected.")

    return hull, warnings
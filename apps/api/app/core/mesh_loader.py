import rhino3dm
import trimesh
import numpy as np

class MeshLoadError(Exception):
    """Raised when a .3dm file cannot be parsed into a usable hull mesh."""
    pass

def load_hull_mesh(filepath: str) -> trimesh.Trimesh:
    model = rhino3dm.File3dm.Read(filepath)
    if model is None:
        raise MeshLoadError(f"Could not read .3dm file at {filepath}")

    all_vertices = []
    all_faces = []
    vertex_offset = 0

    for obj in model.Objects:
        geom = obj.Geometry
        if not isinstance(geom, rhino3dm.Mesh):
            continue
            
        mesh = geom
        if len(mesh.Vertices) == 0:
            continue

        # 1. ดึง Vertices
        verts = np.array([[v.X, v.Y, v.Z] for v in mesh.Vertices], dtype=np.float64)
        
        # 2. ดึง Faces ด้วยวิธีที่ถูกต้องสำหรับ rhino3dm Python
        faces_list = []
        for face in mesh.Faces:
            # ใช้ attribute .IsQuad ของ face object โดยตรง
            if face.IsQuad:
                # Quad มี 4 จุด: A, B, C, D
                faces_list.append([face.A, face.B, face.C])
                faces_list.append([face.A, face.C, face.D])
            else:
                # Triangle มี 3 จุด: A, B, C
                faces_list.append([face.A, face.B, face.C])
        
        faces = np.array(faces_list, dtype=np.int64) + vertex_offset

        all_vertices.append(verts)
        all_faces.append(faces)
        vertex_offset += len(verts)

    if not all_vertices:
        raise MeshLoadError("No Mesh geometry found. Ensure hull is exported as a Polygon Mesh.")

    hull = trimesh.Trimesh(
        vertices=np.vstack(all_vertices), 
        faces=np.vstack(all_faces), 
        process=True
    )
    
    if hull.is_empty:
        raise MeshLoadError("Failed to create a valid Trimesh object.")

    return hull

def validate_and_repair(hull: trimesh.Trimesh) -> tuple[trimesh.Trimesh, list[str]]:
    warnings = []
    if not hull.is_watertight:
        hull.fill_holes()
        hull.process()
        if hull.is_watertight:
            warnings.append("Source mesh had small gaps; automatically repaired.")
    
    if hull.volume < 0:
        hull.invert()
        warnings.append("Mesh face winding was inverted; normals corrected.")

    return hull, warnings
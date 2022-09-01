"""
scyjava Converters for converting between ImageJ2 Meshes and napari Surfaces
"""
import numpy as np
from jpype import JArray, JDouble
from napari.layers import Surface
from scyjava import Priority

from napari_imagej.java import jc
from napari_imagej.types.converters import java_to_py_converter, py_to_java_converter


@java_to_py_converter(
    predicate=lambda obj: isinstance(obj, jc.Mesh), priority=Priority.VERY_HIGH
)
def _mesh_to_surface(mesh: "jc.Mesh") -> Surface:
    """Converts an ImageJ2 Mesh into a napari Surface"""
    # Vertices
    vertices = mesh.vertices()
    py_vertices = np.zeros((vertices.size(), 3))
    position = JArray(JDouble)(3)
    for i, vertex in enumerate(vertices):
        vertex.localize(position)
        py_vertices[i, :] = position
    # Triangles
    triangles = mesh.triangles()
    py_triangles = np.zeros((triangles.size(), 3), dtype=np.int64)
    for i, triangle in enumerate(triangles):
        py_triangles[i, 0] = triangle.vertex0()
        py_triangles[i, 1] = triangle.vertex1()
        py_triangles[i, 2] = triangle.vertex2()
    return Surface(data=(py_vertices, py_triangles))


@py_to_java_converter(
    predicate=lambda obj: isinstance(obj, Surface), priority=Priority.VERY_HIGH
)
def _surface_to_mesh(surface: Surface) -> "jc.Mesh":
    """Converts a napari Surface into an ImageJ2 Mesh"""
    if surface.ndim != 3:
        raise ValueError("Can only convert 3D Surfaces to Meshes!")
    # Surface data is vertices, triangles, colormap data
    py_vertices, py_triangles, _ = surface.data

    mesh: "jc.Mesh" = jc.NaiveDoubleMesh()
    # TODO: Determine the normals
    for py_vertex in py_vertices:
        mesh.vertices().add(*py_vertex)
    for py_triangle in py_triangles:
        mesh.triangles().add(*py_triangle)
    return mesh

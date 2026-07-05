import math
import numpy as np

def generate_icosahedron():
    """
    Generates the vertices and triangular faces of a regular icosahedron centered at the origin.
    Returns:
        vertices: numpy array of shape (12, 3)
        faces: list of 20 tuples, each containing 3 vertex indices (0-11)
    """
    # Golden ratio
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    
    # Vertices of a regular icosahedron
    vertices = np.array([
        [-1,  phi,  0],
        [ 1,  phi,  0],
        [-1, -phi,  0],
        [ 1, -phi,  0],
        [ 0, -1,  phi],
        [ 0,  1,  phi],
        [ 0, -1, -phi],
        [ 0,  1, -phi],
        [ phi, 0, -1],
        [ phi, 0,  1],
        [-phi, 0, -1],
        [-phi, 0,  1]
    ], dtype=float)
    
    # Normalize vertices to lie on a unit sphere
    norms = np.linalg.norm(vertices, axis=1, keepdims=True)
    vertices /= norms

    # Triangular faces (oriented counter-clockwise when viewed from outside)
    faces = [
        (0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
        (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
        (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
        (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)
    ]
    
    return vertices, faces

def map_sphere_to_rolled_d20(x, y, z):
    """
    Maps 3D spherical coordinates to a 2D flat unfolded icosahedron net layout.
    """
    # Simple projection approximation for 2D presentation
    # Convert sphere position to latitude/longitude
    lon = math.atan2(y, x)
    lat = math.asin(z)
    
    # Map to 2D canvas coordinates
    col = (lon + math.pi) / (2 * math.pi) * 800
    row = (lat + math.pi/2) / math.pi * 600
    return col, row

import math

from voxel.renderer import VoxelRenderer

VERTEX_REACH = 2.5
EDGE_REACH = 2.0


def nearest_vertex(frame, col, row):
    best, best_d = None, VERTEX_REACH
    for i, (px, py, _pz) in enumerate(frame.points):
        d = math.hypot(col - px, (row - py) * frame.aspect)
        if d <= best_d:
            best, best_d = i, d
    return best


def nearest_edge(frame, edges, col, row):
    best, best_d = None, EDGE_REACH
    aspect = frame.aspect
    count = len(frame.points)
    for i, (a, b) in enumerate(edges):
        if not (0 <= a < count and 0 <= b < count):
            continue
        ax, ay, az = frame.points[a]
        bx, by, bz = frame.points[b]
        dx, dy = bx - ax, (by - ay) * aspect
        length = dx * dx + dy * dy
        if length == 0:
            continue
        t = max(0.0, min(1.0, ((col - ax) * dx + (row - ay) * aspect * dy) / length))
        d = math.hypot(col - (ax + dx * t), (row - ay) * aspect - dy * t)
        if d <= best_d:
            best, best_d = (i, t, (ax + dx * t, ay + (by - ay) * t, az + (bz - az) * t)), d
    return best


def screen_to_model(frame, sx, sy, depth, matrix):
    rx = (sx - frame.cx) / frame.fit
    ry = -(sy - frame.cy) * frame.aspect / frame.fit
    return VoxelRenderer.unrotate_point(rx, ry, depth, matrix)

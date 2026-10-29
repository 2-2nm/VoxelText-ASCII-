import math
from collections import namedtuple

VoxelFrame = namedtuple("VoxelFrame", "grid points fit cx cy radius aspect owners")

IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def _mat_x(a):
    c, s = math.cos(a), math.sin(a)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _mat_y(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def _mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def _orthonormalize(m):
    r0 = _unit(m[0])
    d = sum(a * b for a, b in zip(m[1], r0))
    r1 = _unit(tuple(a - d * b for a, b in zip(m[1], r0)))
    r2 = (r0[1] * r1[2] - r0[2] * r1[1], r0[2] * r1[0] - r0[0] * r1[2], r0[0] * r1[1] - r0[1] * r1[0])
    return r0, r1, r2


class VoxelRenderer:
    FILL = 0.45
    MIN_RADIUS = 0.5

    @staticmethod
    def initial_rotation():
        return VoxelRenderer.turn(IDENTITY, 0.6, 0.4)

    @staticmethod
    def turn(matrix, yaw, pitch):
        return _orthonormalize(_mul(_mat_x(pitch), _mul(_mat_y(yaw), matrix)))

    @staticmethod
    def rotate_point(x, y, z, m):
        return (
            m[0][0] * x + m[0][1] * y + m[0][2] * z,
            m[1][0] * x + m[1][1] * y + m[1][2] * z,
            m[2][0] * x + m[2][1] * y + m[2][2] * z,
        )

    @staticmethod
    def unrotate_point(x, y, z, m):
        return (
            m[0][0] * x + m[1][0] * y + m[2][0] * z,
            m[0][1] * x + m[1][1] * y + m[2][1] * z,
            m[0][2] * x + m[1][2] * y + m[2][2] * z,
        )

    @staticmethod
    def model_radius(model):
        farthest = max((math.sqrt(x * x + y * y + z * z) for x, y, z in model.vertices), default=1.0)
        return max(farthest, VoxelRenderer.MIN_RADIUS)

    @classmethod
    def render(cls, model, cols, rows, matrix, cell_aspect=2.0, radius=None, zoom=1.0, pan=(0.0, 0.0)):
        grid = [[None] * cols for _ in range(rows)]
        owners = [[-1] * cols for _ in range(rows)]
        radius = radius or cls.model_radius(model)
        fit = cls.FILL * zoom * min(cols, rows * cell_aspect) / radius
        cx, cy = (cols - 1) / 2.0 + pan[0], (rows - 1) / 2.0 + pan[1]
        frame = VoxelFrame(grid, [], fit, cx, cy, radius, cell_aspect, owners)
        if not model.vertices or cols < 2 or rows < 2:
            return frame

        depth = [[-math.inf] * cols for _ in range(rows)]
        for vx, vy, vz in model.vertices:
            rx, ry, rz = cls.rotate_point(vx, vy, vz, matrix)
            frame.points.append((cx + rx * fit, cy - ry * fit / cell_aspect, rz))

        count = len(frame.points)
        for edge, (i1, i2) in enumerate(model.edges):
            if not (0 <= i1 < count and 0 <= i2 < count):
                continue
            x0, y0, z0 = frame.points[i1]
            x1, y1, z1 = frame.points[i2]
            steps = max(int(round(max(abs(x1 - x0), abs(y1 - y0)))), 1)

            for i in range(steps + 1):
                t = i / steps
                px = int(round(x0 + (x1 - x0) * t))
                py = int(round(y0 + (y1 - y0) * t))
                pz = (z0 + (z1 - z0) * t) / radius
                if 0 <= px < cols and 0 <= py < rows and pz > depth[py][px]:
                    depth[py][px] = pz
                    grid[py][px] = max(0.0, min(1.0, (pz + 1.0) / 2.0))
                    owners[py][px] = edge

        return frame

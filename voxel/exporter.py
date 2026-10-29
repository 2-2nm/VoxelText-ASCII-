import json

class VoxelExporter:
    @staticmethod
    def export_to_json(model, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(model.to_dict(), f, indent=2)

    @staticmethod
    def import_from_json(model, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            model.from_dict(data)

    @staticmethod
    def generate_standalone_script(model, cols=32, rows=18, fps=25):
        delay = 1.0 / fps
        vertices_str = json.dumps(model.vertices)
        edges_str = json.dumps(model.edges)
        ramp_str = model.ascii_ramp if model.ascii_ramp else " .:-=+*#%@"

        script = f"""import math
import time
import sys

VERTICES = {vertices_str}
EDGES = {edges_str}
RAMP = "{ramp_str}"
ROT_X = {model.rot_x}
ROT_Y = {model.rot_y}
ROT_Z = {model.rot_z}
COLS, ROWS = {cols}, {rows}

def rotate_point(x, y, z, ax, ay, az):
    cx, sx = math.cos(ax), math.sin(ax)
    y, z = y * cx - z * sx, y * sx + z * cx

    cy, sy = math.cos(ay), math.sin(ay)
    x, z = x * cy + z * sy, -x * sy + z * cy

    cz, sz = math.cos(az), math.sin(az)
    x, y = x * cz - y * sz, x * sz + y * cz

    return x, y, z

def render_frame(ax, ay, az):
    buffer = [[' ' for _ in range(COLS)] for _ in range(ROWS)]
    z_buf = [[-999.0 for _ in range(COLS)] for _ in range(ROWS)]

    cx, cy = COLS / 2.0, ROWS / 2.0
    sx_scale, sy_scale = COLS * 0.4, ROWS * 0.4

    projected = []
    for vx, vy, vz in VERTICES:
        rx, ry, rz = rotate_point(vx, vy, vz, ax, ay, az)
        px = int(cx + rx * sx_scale)
        py = int(cy - ry * sy_scale)
        projected.append((px, py, rz))

    for idx1, idx2 in EDGES:
        if idx1 < len(projected) and idx2 < len(projected):
            x0, y0, z0 = projected[idx1]
            x1, y1, z1 = projected[idx2]

            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            steps = max(dx, dy, 1)

            for i in range(steps + 1):
                t = i / steps
                rx = int(x0 + (x1 - x0) * t)
                ry = int(y0 + (y1 - y0) * t)
                rz = z0 + (z1 - z0) * t

                if 0 <= rx < COLS and 0 <= ry < ROWS:
                    if rz > z_buf[ry][rx]:
                        z_buf[ry][rx] = rz
                        norm_z = (rz + 1.0) / 2.0
                        char_idx = int(max(0.0, min(1.0, norm_z)) * (len(RAMP) - 1))
                        buffer[ry][rx] = RAMP[char_idx]

    return "\\n".join("".join(row) for row in buffer)

def main():
    ax, ay, az = 0.0, 0.0, 0.0
    sys.stdout.write("\\033[2J")
    try:
        while True:
            frame = render_frame(ax, ay, az)
            sys.stdout.write("\\033[H")
            sys.stdout.write("\\033[36m" + frame + "\\033[0m\\n")
            sys.stdout.flush()
            ax += ROT_X
            ay += ROT_Y
            az += ROT_Z
            time.sleep({delay})
    except KeyboardInterrupt:
        sys.stdout.write("\\nDone.\\n")

if __name__ == "__main__":
    main()
"""
        return script
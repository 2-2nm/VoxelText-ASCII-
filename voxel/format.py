import re
import struct

MAGIC = b"VXL"
VERSION = 3
EXTENSION = ".vxl"
MAX_COUNT = 0xFFFF

FLAG_EDGE_COLORS = 1

INK_NONE = 0
INK_MONO = 1
INK_FULL = 2
INK_CUSTOM = 3
INK_MODES = (INK_NONE, INK_MONO, INK_FULL, INK_CUSTOM)

# v1 header: magic, version, flags, spin x/y/z, vertex count, edge count.
# v2 header: the v1 header followed by the grid (columns, rows) the model was edited at.
# v3 header: the v2 header followed by the ink it was edited with (mode, r, g, b).
# v3 body: vertices, edges, then one (painted, r, g, b) record per edge when FLAG_EDGE_COLORS is set.
_HEADER_V1 = struct.Struct("<3sBB3fHH")
_HEADER_V2 = struct.Struct("<3sBB3fHHHH")
_HEADER_V3 = struct.Struct("<3sBB3fHHHH4B")
_HEADERS = {1: _HEADER_V1, 2: _HEADER_V2, 3: _HEADER_V3}
_VERTEX = struct.Struct("<3f")
_EDGE = struct.Struct("<2H")
_EDGE_COLOR = struct.Struct("<4B")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _clamp_u16(value):
    return max(0, min(MAX_COUNT, int(value)))


def _rgb(color):
    if not isinstance(color, str) or not _HEX.match(color):
        raise ValueError(f"Invalid color {color!r}.")
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def _hex(r, g, b):
    return f"#{r:02X}{g:02X}{b:02X}"


def _pack_edge_color(color):
    return _EDGE_COLOR.pack(0, 0, 0, 0) if not color else _EDGE_COLOR.pack(1, *_rgb(color))


def _unpack_edge_color(data, offset):
    painted, r, g, b = _EDGE_COLOR.unpack_from(data, offset)
    return _hex(r, g, b) if painted else None


def encode(vertices, edges, spin=(0.0, 0.0, 0.0), render=None, ink=None, edge_colors=None):
    if len(vertices) > MAX_COUNT or len(edges) > MAX_COUNT:
        raise ValueError("Model is too large for the VXL format.")
    colors = list(edge_colors) if edge_colors else []
    if colors and len(colors) != len(edges):
        raise ValueError("Edge colors do not match the edges.")
    painted = any(colors)
    mode, base = ink or (INK_NONE, "#000000")
    if mode not in INK_MODES:
        raise ValueError(f"Unknown ink mode {mode}.")
    cols, rows = render or (0, 0)
    out = bytearray(_HEADER_V3.pack(
        MAGIC, VERSION, FLAG_EDGE_COLORS if painted else 0, *map(float, spin), len(vertices), len(edges),
        _clamp_u16(cols), _clamp_u16(rows), mode, *_rgb(base),
    ))
    for x, y, z in vertices:
        out += _VERTEX.pack(float(x), float(y), float(z))
    for a, b in edges:
        out += _EDGE.pack(int(a), int(b))
    if painted:
        for color in colors:
            out += _pack_edge_color(color)
    return bytes(out)


def decode(data):
    if len(data) < 4:
        raise ValueError("File is too short to be a VXL model.")
    if data[:3] != MAGIC:
        raise ValueError("Not a VXL file.")
    version = data[3]
    header = _HEADERS.get(version)
    if header is None:
        raise ValueError(f"Unsupported VXL version {version}.")
    if len(data) < header.size:
        raise ValueError("File is too short to be a VXL model.")

    fields = header.unpack_from(data, 0)
    flags = fields[2]
    sx, sy, sz, nv, ne = fields[3:8]
    render = None
    if version >= 2 and fields[8] > 0 and fields[9] > 0:
        render = (fields[8], fields[9])
    ink = None
    if version >= 3 and fields[10] != INK_NONE:
        if fields[10] not in INK_MODES:
            raise ValueError(f"Unknown ink mode {fields[10]}.")
        ink = (fields[10], _hex(*fields[11:14]))
    painted = version >= 3 and bool(flags & FLAG_EDGE_COLORS)
    expected = header.size + nv * _VERTEX.size + ne * _EDGE.size + (ne * _EDGE_COLOR.size if painted else 0)
    if len(data) != expected:
        raise ValueError("VXL file size does not match its header.")

    offset = header.size
    vertices = []
    for _ in range(nv):
        vertices.append(list(_VERTEX.unpack_from(data, offset)))
        offset += _VERTEX.size
    edges = []
    for _ in range(ne):
        a, b = _EDGE.unpack_from(data, offset)
        offset += _EDGE.size
        if a >= nv or b >= nv:
            raise ValueError("VXL edge references a missing vertex.")
        edges.append([a, b])
    edge_colors = [None] * ne
    if painted:
        for i in range(ne):
            edge_colors[i] = _unpack_edge_color(data, offset)
            offset += _EDGE_COLOR.size
    return {
        "vertices": vertices, "edges": edges, "spin": (sx, sy, sz), "render": render,
        "ink": ink, "edge_colors": edge_colors,
    }


def save(path, vertices, edges, spin=(0.0, 0.0, 0.0), render=None, ink=None, edge_colors=None):
    with open(path, "wb") as f:
        f.write(encode(vertices, edges, spin, render, ink, edge_colors))


def load(path):
    with open(path, "rb") as f:
        return decode(f.read())

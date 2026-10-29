import json
import math

class VoxelModel:
    def __init__(self):
        self.vertices = []
        self.edges = []
        self.edge_colors = []
        self.rot_x = 0.03
        self.rot_y = 0.05
        self.rot_z = 0.01
        self.ascii_ramp = " .:-=+*#%@"

    def add_vertex(self, x, y, z):
        self.vertices.append([float(x), float(y), float(z)])
        return len(self.vertices) - 1

    def remove_vertex(self, index):
        if 0 <= index < len(self.vertices):
            self.vertices.pop(index)
            kept = [(e, c) for e, c in zip(self.edges, self.edge_colors) if index not in e]
            self.edges = [[v1 - 1 if v1 > index else v1, v2 - 1 if v2 > index else v2] for (v1, v2), _ in kept]
            self.edge_colors = [c for _, c in kept]

    def move_vertex(self, index, x, y, z):
        if 0 <= index < len(self.vertices):
            self.vertices[index] = [float(x), float(y), float(z)]

    def split_edge(self, edge_index, t):
        a, b = self.edges[edge_index]
        va, vb = self.vertices[a], self.vertices[b]
        new = self.add_vertex(*(p + (q - p) * t for p, q in zip(va, vb)))
        self.edges[edge_index] = [a, new]
        self.edges.append([new, b])
        self.edge_colors.append(self.edge_colors[edge_index])
        return new

    def delete_vertex(self, index):
        incident = [(e[1] if e[0] == index else e[0], c) for e, c in zip(self.edges, self.edge_colors) if index in e]
        self.remove_vertex(index)
        if len(incident) == 2 and incident[0][0] != incident[1][0]:
            a, b = (n - 1 if n > index else n for n, _ in incident)
            self.add_edge(a, b, incident[0][1] or incident[1][1])

    def add_edge(self, v1, v2, color=None):
        if 0 <= v1 < len(self.vertices) and 0 <= v2 < len(self.vertices):
            if v1 != v2 and [v1, v2] not in self.edges and [v2, v1] not in self.edges:
                self.edges.append([v1, v2])
                self.edge_colors.append(color)

    def remove_edge(self, v1, v2):
        kept = [(e, c) for e, c in zip(self.edges, self.edge_colors) if e != [v1, v2] and e != [v2, v1]]
        self.edges = [e for e, _ in kept]
        self.edge_colors = [c for _, c in kept]

    def paint_edges(self, indices, color):
        for i in indices:
            if 0 <= i < len(self.edge_colors):
                self.edge_colors[i] = color

    def connected_edges(self, index):
        if not 0 <= index < len(self.edges):
            return []
        touching = {}
        for i, (a, b) in enumerate(self.edges):
            touching.setdefault(a, []).append(i)
            touching.setdefault(b, []).append(i)
        seen, found, stack = set(), set(), list(self.edges[index])
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            for i in touching.get(v, ()):
                found.add(i)
                stack.extend(self.edges[i])
        return sorted(found)

    def set_geometry(self, vertices, edges, colors=None):
        self.vertices = vertices
        self.edges = edges
        colors = list(colors or [])
        self.edge_colors = (colors + [None] * len(edges))[:len(edges)]

    def snapshot(self):
        return [v[:] for v in self.vertices], [e[:] for e in self.edges], list(self.edge_colors)

    def restore(self, snap):
        self.set_geometry(*snap)

    def clear(self):
        self.vertices = []
        self.edges = []
        self.edge_colors = []

    def to_dict(self):
        return {
            "vertices": self.vertices,
            "edges": self.edges,
            "edgeColors": self.edge_colors,
            "rotX": self.rot_x,
            "rotY": self.rot_y,
            "rotZ": self.rot_z,
            "asciiRamp": self.ascii_ramp
        }

    def from_dict(self, data):
        self.set_geometry(data.get("vertices", []), data.get("edges", []), data.get("edgeColors"))
        self.rot_x = data.get("rotX", 0.03)
        self.rot_y = data.get("rotY", 0.05)
        self.rot_z = data.get("rotZ", 0.01)
        self.ascii_ramp = data.get("asciiRamp", " .:-=+*#%@")

    def save_json(self, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    def load_json(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.from_dict(data)

    def load_preset(self, name):
        self.clear()
        if name == "cube":
            s = 0.6
            self.vertices = [
                [-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s],
                [-s, -s,  s], [s, -s,  s], [s, s,  s], [-s, s,  s]
            ]
            self.edges = [
                [0,1], [1,2], [2,3], [3,0],
                [4,5], [5,6], [6,7], [7,4],
                [0,4], [1,5], [2,6], [3,7]
            ]
        elif name == "pyramid":
            self.vertices = [
                [0.0, 0.8, 0.0],
                [-0.6, -0.6, -0.6],
                [0.6, -0.6, -0.6],
                [0.6, -0.6, 0.6],
                [-0.6, -0.6, 0.6]
            ]
            self.edges = [
                [0,1], [0,2], [0,3], [0,4],
                [1,2], [2,3], [3,4], [4,1]
            ]
        elif name == "torus":
            R, r = 0.6, 0.25
            N, M = 8, 6
            for i in range(N):
                u = (i / N) * math.pi * 2
                for j in range(M):
                    v = (j / M) * math.pi * 2
                    x = (R + r * math.cos(v)) * math.cos(u)
                    y = (R + r * math.cos(v)) * math.sin(u)
                    z = r * math.sin(v)
                    self.vertices.append([x, y, z])
            for i in range(N):
                for j in range(M):
                    curr = i * M + j
                    next_m = i * M + ((j + 1) % M)
                    next_n = ((i + 1) % N) * M + j
                    self.edges.append([curr, next_m])
                    self.edges.append([curr, next_n])
        elif name == "starship":
            self.vertices = [
                [0.0, 0.9, 0.0],
                [-0.5, -0.5, 0.0],
                [0.5, -0.5, 0.0],
                [0.0, -0.3, 0.3],
                [0.0, -0.7, -0.2]
            ]
            self.edges = [
                [0,1], [0,2], [0,3], [1,2], [1,3], [2,3], [1,4], [2,4], [3,4]
            ]
        self.edge_colors = [None] * len(self.edges)

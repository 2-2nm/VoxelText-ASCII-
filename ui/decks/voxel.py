from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QCheckBox, QSlider

from core.ascii import get_ascii_chars
from ui.decks.base import CUSTOM, ModeDeck
from ui.decks.video import RESUME_BG
from ui.decks.voxel_ink import DEPTH_LEVELS, InkCache
from ui.dialogs import VXL_FILTER, open_file, save_file
from ui.theme import DANGER, contrast_text, render_hex, solid_button_style
from ui.widgets import FlatComboBox, STRETCH, SegmentedButton, badge, button, label, mono, muted_label, row
from voxel import editor
from voxel import format as vxl
from voxel.model import VoxelModel
from voxel.renderer import IDENTITY, VoxelRenderer

PRESETS = ["torus", "cube", "pyramid", "starship", "blank"]
TOOL_EDIT = "Edit"
TOOL_DRAW = "Draw"
TOOL_PAINT = "Paint"
CLICK_PX = 4
UNDO_LIMIT = 100
MANY_POINTS = 150
LOAD_VIEW = (0.25, 0.12)
FRAME_MS = 40
MARKER = "\u2588"
SPIN_LIMIT = 100
ORBIT_PER_PX = 0.006
ZOOM_STEP = 1.1
ZOOM_MIN = 0.2
ZOOM_MAX = 6.0
PAN_COLS = 0.9
PAN_ROWS = 0.45
DOLLY = 1.04
FAST = 3.0
KEY_PAN = {Qt.Key_A: (1, 0), Qt.Key_D: (-1, 0), Qt.Key_E: (0, 1), Qt.Key_Q: (0, -1)}
KEY_DOLLY = {Qt.Key_W: 1, Qt.Key_S: -1}
CAMERA_HINT = (
    "Camera: W/S move in and out, A/D strafe, Q/E down and up (hold Shift to go faster), "
    "middle-drag orbits, Shift+middle-drag pans, scroll zooms toward the mouse."
)
HINT = (
    "Edit: " + CAMERA_HINT + " Click a line to add a point, drag points to reshape, "
    "right-click a point to delete it. Ctrl+Z undoes."
)
DRAW_HINT = (
    "Draw: click empty space to start a line, keep clicking to extend it, click an existing point "
    "or line to join it, right-click empty space to finish. Pick a color in the picker to draw new lines in it "
    "(Full Color / Monochrome go back to the default). " + CAMERA_HINT + " Ctrl+Z undoes."
)
PAINT_HINT = (
    "Paint: click or drag over lines to color them with the picker color, Shift+click colors the whole connected "
    "piece, right-click or right-drag clears a line back to the default color. " + CAMERA_HINT + " Ctrl+Z undoes."
)


def spin_text(value):
    if value == 0:
        return "Off"
    return f"{'Left' if value < 0 else 'Right'} {abs(value)}"


class VoxelDeck(ModeDeck):
    KEY = "voxel"
    TITLE = "Voxel"
    WIDTH_MAX = 200

    tick = Signal()

    def _build_extras(self):
        self.model = VoxelModel()
        self.rotation = VoxelRenderer.initial_rotation()
        self.paused = True
        self.zoom = 1.0
        self.pan = (0.0, 0.0)
        self.selected = None
        self._drag = None
        self._view = None
        self.tool = TOOL_EDIT
        self._undo = []
        self._fixed_radius = None
        self._last_grid = None
        self._keys = set()
        self.brush = None
        self._inks = InkCache()

        self.seg_tool = SegmentedButton([TOOL_EDIT, TOOL_DRAW, TOOL_PAINT], default=TOOL_EDIT)
        self.seg_tool.valueChanged.connect(self._on_tool)
        self.btn_undo = button("Undo", height=22, font=(8, True))
        self.btn_undo.clicked.connect(self.undo)
        self.btn_fit = button("Fit", height=22, font=(8, True))
        self.btn_fit.setToolTip("Reset zoom and position")
        self.btn_fit.clicked.connect(self.reset_view)
        self.chk_points = QCheckBox("Points")
        self.chk_points.setFont(mono(8, True))
        self.chk_points.setChecked(True)
        QShortcut(QKeySequence(QKeySequence.Undo), self, activated=self.undo)

        self.combo_preset = FlatComboBox()
        self.combo_preset.setFixedHeight(22)
        self.combo_preset.addItems(PRESETS)
        self.combo_preset.currentTextChanged.connect(self._on_preset)

        self.btn_load = button("Load VXL", height=22, font=(8, True))
        self.btn_load.clicked.connect(self._load_vxl)
        self.btn_save = button("Save VXL", height=20, font=(8, True))
        self.btn_save.clicked.connect(self._save_vxl)

        self.slider_spin = QSlider(Qt.Horizontal)
        self.slider_spin.setRange(-SPIN_LIMIT, SPIN_LIMIT)
        self.slider_spin.setValue(int(self._settings["voxel_spin"]))
        self.lbl_spin = badge(spin_text(self.slider_spin.value()))
        self.slider_spin.valueChanged.connect(lambda v: self.lbl_spin.setText(spin_text(v)))

        self.btn_pause = button("Resume", font=(8, True))
        self.btn_pause.clicked.connect(self.toggle_pause)

        self.model.load_preset(self.combo_preset.currentText())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def _rows(self):
        return [
            self._style_row(),
            row(muted_label("// PARAMETERS"), STRETCH, self.btn_save),
            row((self.combo_preset, 1), self.btn_load),
            row(label("Tool"), self.seg_tool, STRETCH, self.chk_points, self.btn_fit, self.btn_undo),
            *self._width_rows(),
            row(label("Spin"), (self.slider_spin, 1), self.lbl_spin),
            self.btn_pause,
        ]

    def start_render(self):
        self.timer.start(FRAME_MS)

    def stop_render(self):
        self.timer.stop()
        self._drag = None

    def is_running(self):
        return self.timer.isActive()

    @property
    def background(self):
        return self._colors["bg_surface"]

    def toggle_pause(self):
        self.paused = not self.paused
        self.selected = None
        self._drag = None
        self._refresh_pause_button()
        if self.paused:
            self.log.emit(HINT, "info")
        else:
            self.log.emit("Rotation resumed.", "info")

    def _refresh_pause_button(self):
        btn = self.btn_pause
        if self.paused:
            btn.setText("Resume")
            btn.setStyleSheet(solid_button_style(RESUME_BG, "#08090C"))
        else:
            accent = self._colors["accent"]
            btn.setText("Pause")
            btn.setStyleSheet(solid_button_style(accent, contrast_text(accent)))

    def apply_theme(self, colors, theme):
        super().apply_theme(colors, theme)
        accent = colors["accent"]
        self.seg_tool.set_colors(accent, colors["bg_panel"], contrast_text(accent), colors["text_primary"])
        self._refresh_pause_button()

    def frame(self, cols, rows, aspect):
        spin = self.slider_spin.value()
        if not self.paused and spin:
            self.rotation = VoxelRenderer.turn(self.rotation, spin / 1000.0, 0.0)
        self._last_grid = (cols, rows)
        self._fly()
        radius = self._drag["radius"] if self._drag else self._draw_radius()
        self._view = VoxelRenderer.render(self.model, cols, rows, self.rotation, aspect, radius, self.zoom, self.pan)
        cells = self._to_cells(self._view.grid, self._view.owners)
        if self.paused and self.chk_points.isChecked():
            self._mark_vertices(cells, self._view.points)
        return self._merge(cells)

    def _ramp(self, color=None):
        if color is None:
            color = self.custom_hex if self.color_mode == CUSTOM else render_hex(self.color_mode, self._theme)
        return self._inks.ramp(self.background, color, self.color_mode == "Color")

    def _to_cells(self, grid, owners):
        chars = [c for c in get_ascii_chars(self.color_mode, self.fullcolor_style, "black") if c.strip()] or [MARKER]
        top = len(chars) - 1
        base = self._ramp()
        tints = self.model.edge_colors
        cells = []
        for line, owned in zip(grid, owners):
            out = []
            for cell, edge in zip(line, owned):
                if cell is None:
                    out.append((" ", None))
                    continue
                tint = tints[edge] if 0 <= edge < len(tints) else None
                ramp = base if tint is None else self._ramp(tint)
                out.append((chars[round(cell * top)], ramp[min(DEPTH_LEVELS - 1, int(cell * DEPTH_LEVELS))]))
            cells.append(out)
        return cells

    def _mark_vertices(self, cells, points):
        idle = self._colors["note_tag"]
        order = sorted(range(len(points)), key=lambda i: (i == self.selected, points[i][2]))
        for i in order:
            col, row_ = round(points[i][0]), round(points[i][1])
            if 0 <= row_ < len(cells) and 0 <= col < len(cells[row_]):
                cells[row_][col] = (MARKER, DANGER if i == self.selected else idle)

    def _merge(self, cells):
        lines = []
        for line in cells:
            runs = []
            for char, color in line:
                if color is None:
                    color = runs[-1][1] if runs else self._colors["text_primary"]
                if runs and runs[-1][1] == color:
                    runs[-1][0] += char
                else:
                    runs.append([char, color])
            lines.append(runs)
        return lines

    def handle_wheel(self, delta, col=None, row_=None):
        self._zoom_at(ZOOM_STEP ** (delta / 120.0), col, row_)

    def _zoom_at(self, factor, col=None, row_=None):
        old = self.zoom
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, old * factor))
        view = self._view
        if col is None or view is None:
            return
        k = self.zoom / old
        self.pan = (self.pan[0] + (col - view.cx) * (1 - k), self.pan[1] + (row_ - view.cy) * (1 - k))

    def handle_key(self, key, pressed):
        if key == -1:
            self._keys.clear()
        elif pressed:
            self._keys.add(key)
        else:
            self._keys.discard(key)

    def _fly(self):
        if not self._keys or self._view is None:
            return
        speed = FAST if Qt.Key_Shift in self._keys else 1.0
        dx = sum(KEY_PAN[k][0] for k in self._keys if k in KEY_PAN)
        dy = sum(KEY_PAN[k][1] for k in self._keys if k in KEY_PAN)
        if dx or dy:
            self.pan = (self.pan[0] + dx * PAN_COLS * speed, self.pan[1] + dy * PAN_ROWS * speed)
        move = sum(KEY_DOLLY[k] for k in self._keys if k in KEY_DOLLY)
        if move:
            old = self.zoom
            self._zoom_at(DOLLY ** (move * speed))
            k = self.zoom / old
            self.pan = (self.pan[0] * k, self.pan[1] * k)

    def reset_view(self):
        self.zoom = 1.0
        self.pan = (0.0, 0.0)

    def handle_mouse(self, kind, col, row_, button_name, x=0, y=0):
        view = self._view
        drawing = self.tool == TOOL_DRAW
        if not self.paused or view is None or not (view.points or drawing):
            return
        if kind == "press" and button_name == "left":
            if drawing:
                self._press_draw(view, col, row_, x, y)
            elif self.tool == TOOL_PAINT:
                self._press_paint(view, col, row_, x, y, self._paint_color())
            else:
                self._press(view, col, row_, x, y)
        elif kind == "press" and button_name == "middle":
            if Qt.Key_Shift in self._keys:
                self._drag = {"pan": True, "last": (col, row_), "radius": view.radius, "travel": 0}
            else:
                self._start_orbit(view, x, y)
        elif kind == "press" and button_name == "right":
            if self.tool == TOOL_PAINT:
                self._press_paint(view, col, row_, x, y, None)
            elif not self._delete(view, col, row_):
                self.selected = None
                self._start_orbit(view, x, y)
        elif kind == "move" and self._drag:
            self._move(view, col, row_, x, y)
        elif kind == "release" and self._drag:
            drag, self._drag = self._drag, None
            if drag.get("place") and drag["travel"] < CLICK_PX:
                self._place(view, *drag["place"])

    def _press(self, view, col, row_, x, y):
        index = editor.nearest_vertex(view, col, row_)
        origin = None
        snap = None
        if index is not None:
            origin = view.points[index]
            snap = self._snapshot()
        else:
            hit = editor.nearest_edge(view, self.model.edges, col, row_)
            if hit is not None:
                self._push_undo()
                index = self.model.split_edge(hit[0], hit[1])
                origin = hit[2]
        self.selected = index
        if index is None:
            self._start_orbit(view, x, y)
            return
        self._drag = {"index": index, "grab": (col, row_), "origin": origin, "radius": view.radius, "snap": snap}

    def _press_draw(self, view, col, row_, x, y):
        index = editor.nearest_vertex(view, col, row_)
        if index is None:
            hit = editor.nearest_edge(view, self.model.edges, col, row_)
            if hit is None:
                self._start_orbit(view, x, y)
                self._drag["place"] = (col, row_)
                return
            self._push_undo()
            index = self.model.split_edge(hit[0], hit[1])
        else:
            self._push_undo()
        if self.selected is not None and self.selected != index:
            self.model.add_edge(self.selected, index, self.brush)
        self.selected = index

    def _paint_color(self):
        return self.brush or self.custom_hex

    def _press_paint(self, view, col, row_, x, y, color):
        hit = editor.nearest_edge(view, self.model.edges, col, row_)
        if hit is None:
            self._start_orbit(view, x, y)
            return
        self._push_undo()
        whole = Qt.Key_Shift in self._keys
        self.model.paint_edges(self.model.connected_edges(hit[0]) if whole else [hit[0]], color)
        self._drag = {"paint": True, "color": color, "radius": view.radius, "travel": 0}

    def _paint_under(self, view, col, row_):
        hit = editor.nearest_edge(view, self.model.edges, col, row_)
        if hit is not None:
            self.model.paint_edges([hit[0]], self._drag["color"])

    def _place(self, view, col, row_):
        depth = 0.0
        if self.selected is not None and self.selected < len(view.points):
            depth = view.points[self.selected][2]
        self._push_undo()
        x, y, z = editor.screen_to_model(view, col, row_, depth, self.rotation)
        index = self.model.add_vertex(x, y, z)
        if self.selected is not None:
            self.model.add_edge(self.selected, index, self.brush)
        self.selected = index

    def _start_orbit(self, view, x, y):
        self._drag = {"orbit": True, "last": (x, y), "radius": view.radius, "travel": 0}

    def _orbit(self, x, y):
        d = self._drag
        dx, dy = x - d["last"][0], y - d["last"][1]
        d["last"] = (x, y)
        d["travel"] += abs(dx) + abs(dy)
        if d["travel"] >= CLICK_PX:
            self.rotation = VoxelRenderer.turn(self.rotation, dx * ORBIT_PER_PX, dy * ORBIT_PER_PX)

    def _move(self, view, col, row_, x, y):
        d = self._drag
        if d.get("orbit"):
            self._orbit(x, y)
            return
        if d.get("paint"):
            self._paint_under(view, col, row_)
            return
        if d.get("pan"):
            self.pan = (self.pan[0] + col - d["last"][0], self.pan[1] + row_ - d["last"][1])
            d["last"] = (col, row_)
            return
        if d.get("snap") is not None:
            self._push_undo(d["snap"])
            d["snap"] = None
        sx = d["origin"][0] + (col - d["grab"][0])
        sy = d["origin"][1] + (row_ - d["grab"][1])
        mx, my, mz = editor.screen_to_model(view, sx, sy, d["origin"][2], self.rotation)
        self.model.move_vertex(d["index"], mx, my, mz)

    def _delete(self, view, col, row_):
        index = editor.nearest_vertex(view, col, row_)
        if index is None:
            return False
        self._push_undo()
        self.model.delete_vertex(index)
        self.selected = None
        self._drag = None
        return True

    def _draw_radius(self):
        if self.tool != TOOL_DRAW or not self.paused:
            return None
        if self._fixed_radius is None:
            self._fixed_radius = max(VoxelRenderer.model_radius(self.model), 1.0)
        return self._fixed_radius

    def _snapshot(self):
        return self.model.snapshot()

    def _push_undo(self, snap=None):
        self._undo.append(snap or self._snapshot())
        del self._undo[:-UNDO_LIMIT]

    def undo(self):
        if not self.paused or not self._undo:
            return
        self.model.restore(self._undo.pop())
        self.selected = None
        self._drag = None

    def _on_tool(self, tool):
        self.tool = tool
        self.selected = None
        self._drag = None
        self._fixed_radius = None
        self.picker.set_color(self.custom_hex if tool == TOOL_EDIT else self._paint_color())
        self.log.emit({TOOL_DRAW: DRAW_HINT, TOOL_PAINT: PAINT_HINT}.get(tool, HINT), "info")

    def _on_preset(self, name):
        self._push_undo()
        self._fixed_radius = None
        self.pan = (0.0, 0.0)
        self.model.load_preset(name)
        self.selected = None
        self._drag = None

    def _load_vxl(self):
        path = open_file(self, "Load Voxel Model", VXL_FILTER)
        if not path:
            return
        try:
            data = vxl.load(path)
        except (OSError, ValueError) as e:
            self.log.emit(f"Failed to load voxel model: {e}", "err")
            return
        self._push_undo()
        self.model.set_geometry(data["vertices"], data["edges"], data["edge_colors"])
        self._apply_ink(data["ink"])
        self._fixed_radius = None
        self.rotation = VoxelRenderer.turn(IDENTITY, *LOAD_VIEW)
        self.slider_spin.setValue(max(-SPIN_LIMIT, min(SPIN_LIMIT, round(data["spin"][1] * 1000))))
        self.selected = None
        self._drag = None
        self.zoom = 1.0
        self.pan = (0.0, 0.0)
        painted = sum(1 for c in self.model.edge_colors if c)
        note = f", {painted} colored lines" if painted else ""
        note += f" (edited at {data['render'][0]}x{data['render'][1]})" if data.get("render") else " (v1: no edit width recorded)"
        self.log.emit(f"Voxel model loaded: {path}{note}", "info")
        if len(self.model.vertices) > MANY_POINTS:
            self.chk_points.setChecked(False)
            self.log.emit("Point markers hidden for this detailed model (tick 'Points' to edit it).", "info")

    def _save_vxl(self):
        path = save_file(self, "Save Voxel Model", f"model_3d{vxl.EXTENSION}", VXL_FILTER)
        if not path:
            return
        if not path.lower().endswith(vxl.EXTENSION):
            path += vxl.EXTENSION
        spin = (0.0, self.slider_spin.value() / 1000.0, 0.0)
        try:
            vxl.save(
                path, self.model.vertices, self.model.edges, spin, self._last_grid,
                self._file_ink(), self.model.edge_colors,
            )
        except (OSError, ValueError) as e:
            self.log.emit(f"Failed to save voxel model: {e}", "err")
            return
        grid = f" (edited at {self._last_grid[0]}x{self._last_grid[1]})" if self._last_grid else ""
        self.log.emit(f"Voxel model saved: {path}{grid}", "info")

    def _file_ink(self):
        mode = {"Color": vxl.INK_FULL, CUSTOM: vxl.INK_CUSTOM}.get(self.color_mode, vxl.INK_MONO)
        return mode, self.render_color(self._theme)[1]

    def _apply_ink(self, ink):
        if ink is None:
            return
        mode, color = ink
        if mode == vxl.INK_CUSTOM:
            self.custom_hex = color
            self.picker.set_color(color)
            self.select_color_mode(CUSTOM, emit=False)
        else:
            self.select_color_mode("Color" if mode == vxl.INK_FULL else "White", emit=False)

    def select_color_mode(self, value, emit=True):
        self.brush = None
        super().select_color_mode(value, emit)

    def _on_picker_dragged(self, hex_color):
        if self.tool == TOOL_EDIT:
            super()._on_picker_dragged(hex_color)
        else:
            self.brush = hex_color

    def _on_picker_released(self, hex_color):
        if self.tool == TOOL_EDIT:
            super()._on_picker_released(hex_color)
        else:
            self.brush = hex_color

    def load_state(self, s):
        super().load_state(s)
        preset = s["voxel_preset"]
        if preset in PRESETS:
            self.combo_preset.setCurrentText(preset)
        self.slider_spin.setValue(int(s["voxel_spin"]))

    def get_state(self):
        state = {**super().get_state(), "voxel_preset": self.combo_preset.currentText()}
        state["voxel_spin"] = self.slider_spin.value()
        return state

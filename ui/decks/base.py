from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QScrollArea, QSlider, QVBoxLayout, QWidget

from core.ascii import CHARSET_NAMES, get_charset
from ui.color_picker import ColorPicker
from ui.theme import (
    DANGER, DEFAULT_RENDER_HEX, LEGACY_COLORS, MODE_ACCENTS, PALETTE, contrast_text, render_hex, solid_button_style,
)
from ui.widgets import FlatComboBox, STRETCH, SegmentedButton, badge, button, column, label, labeled_row, mono, muted_label, row


PALETTE_TEXT_ALIGN = " text-align: left; padding-left: 10px;"
CUSTOM = "Custom"


class ModeDeck(QWidget):
    KEY = ""
    TITLE = ""
    WIDTH_MAX = 500
    PALETTE_WIDTH = 170
    MONOCHROME_HEX = None

    log = Signal(str, str)
    colorModeChanged = Signal(str)
    styleChanged = Signal(str)
    transparencyChanged = Signal(str)
    charsetChanged = Signal(str)

    def __init__(self, settings, colors, theme, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._colors = colors
        self._theme = theme
        self.color_mode = settings[f"{self.KEY}_color_mode"]
        self.color_buttons = {}

        self._build_common(settings)
        self._build_extras()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._build_palette_column())
        root.addWidget(column(*self._rows(), spacing=2))

    def _build_extras(self):
        pass

    def _rows(self):
        raise NotImplementedError

    def _build_common(self, settings):
        k = self.KEY

        self.seg_style = SegmentedButton(["Blocky", "Pure ASCII"], default=settings[f"{k}_fullcolor_style"])
        self.seg_style.valueChanged.connect(self.styleChanged)

        self.combo_charset = FlatComboBox()
        self.combo_charset.setFixedHeight(22)
        self.combo_charset.setToolTip("ASCII character set")
        self.combo_charset.addItems(CHARSET_NAMES)
        self.combo_charset.setCurrentText(get_charset())
        self.combo_charset.currentTextChanged.connect(self.charsetChanged)

        self.lbl_width = badge(f"{settings[f'{k}_width']} px")
        self.entry_overdrive = QLineEdit(str(settings[f"{k}_overdrive_val"]))
        self.entry_overdrive.setFixedSize(55, 20)
        self.entry_overdrive.setAlignment(Qt.AlignCenter)
        self.entry_overdrive.hide()

        self.chk_overdrive = QCheckBox("Overdrive")
        self.chk_overdrive.setFont(mono(8, True))
        self.chk_overdrive.setStyleSheet(f"color: {DANGER};")
        self.chk_overdrive.clicked.connect(self._apply_overdrive)

        self.slider_width = QSlider(Qt.Horizontal)
        self.slider_width.setRange(30, self.WIDTH_MAX)
        self.slider_width.setValue(int(settings[f"{k}_width"]))
        self.slider_width.valueChanged.connect(lambda v: self.lbl_width.setText(f"{v} px"))

        self.seg_alpha = SegmentedButton(["Black", "White"], default=str(settings[f"{k}_transparency"]).capitalize())
        self.seg_alpha.valueChanged.connect(lambda v: self.transparencyChanged.emit(v.lower()))

    def _build_palette_column(self):
        holder = QWidget()
        holder.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(2)

        for entry in PALETTE:
            btn = button(entry.label, height=24)
            btn.clicked.connect(lambda checked=False, v=entry.value: self.select_color_mode(v))
            layout.addWidget(btn)
            self.color_buttons[entry.value] = btn
        self._build_custom_color()
        layout.addWidget(self.btn_custom)
        layout.addWidget(self.picker)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.setWidget(holder)

        return column(muted_label("// PALETTE"), scroll, fixed_width=self.PALETTE_WIDTH)

    def _build_custom_color(self):
        self.custom_hex = self._settings.get(f"{self.KEY}_custom_color") or DEFAULT_RENDER_HEX
        self.btn_custom = button("Custom Color", height=24)
        self.btn_custom.clicked.connect(lambda: self.select_color_mode(CUSTOM))
        self.picker = ColorPicker(self.custom_hex)
        self.picker.colorChanged.connect(self._on_picker_dragged)
        self.picker.colorCommitted.connect(self._on_picker_released)

    def _on_picker_dragged(self, hex_color):
        self.custom_hex = hex_color
        self._restyle_palette()

    def _on_picker_released(self, hex_color):
        self.custom_hex = hex_color
        self.select_color_mode(CUSTOM)

    def _style_row(self):
        return row(self.seg_style, self.combo_charset, STRETCH)

    def _width_rows(self):
        return [
            row(label("Width"), STRETCH, self.lbl_width, self.entry_overdrive, self.chk_overdrive),
            self.slider_width,
        ]

    def _alpha_row(self, *extra):
        return labeled_row("Transparency", *extra, self.seg_alpha)

    @property
    def fullcolor_style(self):
        return self.seg_style.get()

    @property
    def transparency(self):
        return self.seg_alpha.get().lower()

    def render_color(self, theme):
        if self.color_mode == CUSTOM:
            return "White", self.custom_hex
        if self.color_mode == "White" and self.MONOCHROME_HEX:
            return "White", self.MONOCHROME_HEX
        return self.color_mode, render_hex(self.color_mode, theme)

    def target_cols(self, on_invalid=None):
        if self.chk_overdrive.isChecked():
            try:
                cols = int(self.entry_overdrive.text().strip())
                if cols > 0:
                    return cols
            except ValueError:
                pass
            if on_invalid:
                on_invalid("Invalid Overdrive value! Reverting to slider width.", "err")
        return round(self.slider_width.value())

    def set_charset(self, name):
        if self.combo_charset.currentText() != name:
            self.combo_charset.blockSignals(True)
            self.combo_charset.setCurrentText(name)
            self.combo_charset.blockSignals(False)

    def _apply_overdrive(self, checked):
        self.lbl_width.setVisible(not checked)
        self.entry_overdrive.setVisible(checked)
        self.slider_width.setEnabled(not checked)
        state, tag = ("ENABLED", "warn") if checked else ("DISABLED", "info")
        self.log.emit(f"{self.TITLE} Overdrive Width {state}", tag)

    def select_color_mode(self, value, emit=True):
        self.color_mode = value
        self._restyle_palette()
        is_color = value == "Color"
        self.seg_alpha.setEnabled(not is_color)
        self.seg_style.setEnabled(is_color)
        if emit:
            self.colorModeChanged.emit(value)

    def _restyle_palette(self):
        c = self._colors
        for entry in PALETTE:
            btn = self.color_buttons[entry.value]
            if entry.value == self.color_mode:
                bg = entry.hex(self._theme)
                btn.setStyleSheet(solid_button_style(bg, contrast_text(bg)) + PALETTE_TEXT_ALIGN)
            else:
                btn.setStyleSheet(self._idle_button_style())
        if self.color_mode == CUSTOM:
            self.btn_custom.setStyleSheet(
                solid_button_style(self.custom_hex, contrast_text(self.custom_hex)) + PALETTE_TEXT_ALIGN)
        else:
            self.btn_custom.setStyleSheet(self._idle_button_style())

    def _idle_button_style(self):
        c = self._colors
        return (f"background-color: {c['bg_panel']}; color: {c['text_primary']}; border-radius: 4px;"
                + PALETTE_TEXT_ALIGN)

    def apply_theme(self, colors, theme):
        self._colors = colors
        self._theme = theme
        accent = MODE_ACCENTS[self.KEY] or colors["accent"]
        for seg in (self.seg_style, self.seg_alpha):
            seg.set_colors(accent, colors["bg_panel"], contrast_text(accent), colors["text_primary"])
        self._restyle_palette()

    def load_state(self, s):
        k = self.KEY
        mode = s[f"{k}_color_mode"]
        custom = s.get(f"{k}_custom_color") or DEFAULT_RENDER_HEX
        if mode in LEGACY_COLORS:
            mode, custom = CUSTOM, LEGACY_COLORS[mode]
        self.custom_hex = custom
        self.picker.set_color(custom)
        width = int(s[f"{k}_width"])
        self.slider_width.setValue(width)
        self.lbl_width.setText(f"{width} px")
        self.seg_alpha.set(str(s[f"{k}_transparency"]).capitalize())
        self.seg_style.set(s[f"{k}_fullcolor_style"])
        self.entry_overdrive.setText(str(s[f"{k}_overdrive_val"]))
        overdrive = bool(s[f"{k}_overdrive"])
        self.chk_overdrive.setChecked(overdrive)
        self._apply_overdrive(overdrive)
        self.select_color_mode(mode, emit=False)

    def get_state(self):
        k = self.KEY
        return {
            f"{k}_color_mode": self.color_mode,
            f"{k}_custom_color": self.custom_hex,
            f"{k}_fullcolor_style": self.fullcolor_style,
            f"{k}_width": round(self.slider_width.value()),
            f"{k}_transparency": self.transparency,
            f"{k}_overdrive": self.chk_overdrive.isChecked(),
            f"{k}_overdrive_val": self.entry_overdrive.text().strip(),
        }

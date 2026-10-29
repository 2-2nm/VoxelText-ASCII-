import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

STRETCH = object()


def mono(size=8, bold=False):
    return QFont("Consolas", size, QFont.Bold if bold else QFont.Normal)


def label(text, size=8, bold=False, name=None):
    lbl = QLabel(text)
    lbl.setFont(mono(size, bold))
    if name:
        lbl.setObjectName(name)
    return lbl


def muted_label(text, size=8, bold=True):
    return label(text, size, bold, "muted")


def badge(text):
    return label(text, 8, True, "badge")


def button(text="", on_click=None, *, size=None, height=None, font=None, style=None):
    btn = QPushButton(text)
    if size:
        btn.setFixedSize(*size)
    if height:
        btn.setFixedHeight(height)
    if font:
        btn.setFont(mono(*font))
    if style:
        btn.setStyleSheet(style)
    if on_click:
        btn.clicked.connect(on_click)
    return btn


def add_all(layout, items):
    for item in items:
        if item is STRETCH:
            layout.addStretch()
        elif isinstance(item, tuple):
            layout.addWidget(*item)
        else:
            layout.addWidget(item)


def row(*items, margins=(0, 0, 0, 0), spacing=None):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(*margins)
    if spacing is not None:
        layout.setSpacing(spacing)
    add_all(layout, items)
    return widget


def column(*items, margins=(0, 0, 0, 0), spacing=None, fixed_width=None):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(*margins)
    if spacing is not None:
        layout.setSpacing(spacing)
    if fixed_width:
        widget.setFixedWidth(fixed_width)
    add_all(layout, items)
    return widget


def labeled_row(text, *right):
    return row(label(text), STRETCH, *right)


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.clicked.emit()


_SEG_BUTTON_QSS = """
    QPushButton {{
        background-color: {bg};
        color: {fg};
        border: none;
        border-radius: 11px;
        padding: 2px 10px;
        font-weight: bold;
    }}
    {hover}
"""
_SEG_HOVER_QSS = "QPushButton:hover { background-color: #2A2F3A; }"


class SegmentedButton(QFrame):
    valueChanged = Signal(str)

    def __init__(self, items, default=None, selected_color="#D5DBE6", unselected_color="#1C2028",
                 text_selected="#08090C", text_unselected="#E6E8EE", parent=None):
        super().__init__(parent)
        self.selected_value = default or (items[0] if items else "")
        self.buttons = {}
        self._colors = (selected_color, unselected_color, text_selected, text_unselected)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self.setStyleSheet("background-color: transparent; border: none;")

        for item in items:
            btn = QPushButton(item)
            btn.setFixedHeight(22)
            btn.setFont(mono(9, True))
            btn.clicked.connect(lambda checked=False, val=item: self.set(val, emit=True))
            layout.addWidget(btn)
            self.buttons[item] = btn

        self._restyle()

    def set_colors(self, selected_color, unselected_color, text_selected, text_unselected):
        self._colors = (selected_color, unselected_color, text_selected, text_unselected)
        self._restyle()

    def set(self, value, emit=False):
        if value in self.buttons:
            self.selected_value = value
            self._restyle()
            if emit:
                self.valueChanged.emit(value)

    def get(self):
        return self.selected_value

    def _restyle(self):
        sel_bg, unsel_bg, sel_fg, unsel_fg = self._colors
        for value, btn in self.buttons.items():
            selected = value == self.selected_value
            btn.setStyleSheet(_SEG_BUTTON_QSS.format(
                bg=sel_bg if selected else unsel_bg,
                fg=sel_fg if selected else unsel_fg,
                hover="" if selected else _SEG_HOVER_QSS,
            ))


class FlatComboBox(QComboBox):
    """QComboBox whose popup has no fade/shadow/translucency.

    On Windows a styled combo popup is a translucent top-level window with a drop shadow; it flashes
    when it opens and whenever the window behind it repaints."""

    def __init__(self, parent=None):
        super().__init__(parent)
        if os.environ.get("VOXELTEXT_NOPOPUPFIX"):
            return
        popup = self.view().window()
        popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        popup.setAttribute(Qt.WA_TranslucentBackground, False)

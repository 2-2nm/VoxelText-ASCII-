from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from game.manager import hide_overlay_window, make_overlay_window, place_overlay_window


class GameOverlayWindow(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #000000;")
        self.setGeometry(-32000, -32000, 64, 64)
        self._label = QLabel(self)
        self._label.setScaledContents(True)
        self._label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._styled = False
        self._visible = False
        self._last_rect = None
        self.create()

    @property
    def is_shown(self):
        return self._visible

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._label.setGeometry(0, 0, self.width(), self.height())

    def set_frame(self, pix):
        self._label.setPixmap(pix)

    def show_at(self, rect):
        hwnd = int(self.winId())
        if not self._styled:
            self.show()
            make_overlay_window(hwnd)
            self._styled = True
        if not self._visible or self._last_rect != rect:
            place_overlay_window(hwnd, *rect)
            self._visible = True
            self._last_rect = rect

    def hide_overlay(self):
        if self._visible:
            hide_overlay_window(int(self.winId()))
            self._visible = False
            self._last_rect = None

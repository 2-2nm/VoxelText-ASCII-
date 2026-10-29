import os

from PySide6.QtCore import QEvent, Qt, QPoint, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QIcon, QImage, QPixmap, QTextCharFormat
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QTextEdit, QVBoxLayout, QWidget

from core.utils import get_resource_path
from ui.widgets import STRETCH, ClickableLabel, add_all, button, mono, muted_label

SCROLL_STEP = 20
MOUSE_KINDS = {QEvent.MouseButtonPress: "press", QEvent.MouseMove: "move", QEvent.MouseButtonRelease: "release"}
MOUSE_BUTTONS = {Qt.LeftButton: "left", Qt.RightButton: "right", Qt.MiddleButton: "middle"}
KEY_EVENTS = {QEvent.KeyPress: True, QEvent.KeyRelease: False}
RELEASE_ALL = -1
CAMERA_KEYS = {Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D, Qt.Key_Q, Qt.Key_E, Qt.Key_Shift}
FRAME_MIN_PX = 4
FRAME_MAX_PX = 32
FRAME_FONT_RATIO = 0.55
ARROW_BUTTONS = [("▲", True, -5), ("▼", True, 5), ("◄", False, -5), ("►", False, 5)]


def pil_to_qpixmap(pil_img):
    if pil_img.mode == "RGB":
        w, h = pil_img.size
        return QPixmap.fromImage(QImage(pil_img.tobytes(), w, h, w * 3, QImage.Format_RGB888))
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    qimg = QImage(pil_img.tobytes("raw", "RGBA"), pil_img.width, pil_img.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


class PreviewPane(QFrame):
    sizeChanged = Signal(int, int)
    frameMouse = Signal(str, int, int, str, int, int)
    frameWheel = Signal(int, int, int)
    frameKey = Signal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("surface")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        layout.addWidget(self._build_header())

        self.text = QTextEdit()
        self.text.setObjectName("txt_ascii")
        self.text.setFont(mono(8))
        self.text.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.text)

        self.label = ClickableLabel()
        self.label.setAlignment(Qt.AlignCenter)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.addWidget(self.label)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(inner)
        self.scroll.hide()
        layout.addWidget(self.scroll)

        self._frame_styled = False
        self._last_style = None
        self._last_lines = None
        self.text.viewport().installEventFilter(self)
        self.text.installEventFilter(self)
        self._frame_fmt = {}

    def _build_header(self):
        header = QFrame()
        header.setObjectName("panel")
        header.setFixedHeight(28)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(8, 2, 8, 2)

        arrows = [
            button(txt, lambda checked=False, v=vertical, a=amount: self.scroll_by(v, a), size=(24, 20))
            for txt, vertical, amount in ARROW_BUTTONS
        ]
        self.btn_toggle_deck = button("Hide Settings", height=20, font=(8, True))
        self.btn_clear = button()
        self.btn_mute = button()

        add_all(layout, [muted_label("TERMINAL OUTPUT PREVIEW"), STRETCH, *arrows,
                         self.btn_toggle_deck, self.btn_clear, self.btn_mute])
        return header

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.sizeChanged.emit(event.size().width(), event.size().height())

    @property
    def image_visible(self):
        return self.scroll.isVisible()

    def show_text(self):
        self._release_frame_style()
        self.scroll.hide()
        self.text.show()

    def show_image(self):
        self._release_frame_style()
        self.text.hide()
        self.scroll.show()

    def frame_grid(self, cols):
        edit = self.text
        margin = edit.document().documentMargin() * 2
        avail_w = max(1.0, edit.viewport().width() - margin)
        avail_h = max(1.0, edit.viewport().height() - margin)

        px = max(FRAME_MIN_PX, min(FRAME_MAX_PX, int(avail_w / (max(cols, 1) * FRAME_FONT_RATIO))))
        while True:
            font = QFont("Consolas", 8)
            font.setStyleHint(QFont.Monospace)
            font.setPixelSize(px)
            metrics = QFontMetricsF(font)
            cell_w = metrics.horizontalAdvance("M")
            cell_h = metrics.lineSpacing()
            if px <= FRAME_MIN_PX or cell_w * cols <= avail_w:
                break
            px -= 1

        frame_cols = max(2, int(avail_w // cell_w) - 1)
        frame_rows = max(2, int(avail_h // cell_h) - 1)
        return font, frame_cols, frame_rows, cell_h / cell_w

    def show_frame(self, lines, font, background):
        edit = self.text
        self.scroll.hide()
        edit.show()
        self._frame_styled = True
        style = (font.pixelSize(), font.family(), background)
        if style != self._last_style:
            self._last_style = style
            self._last_lines = None
            edit.setFont(font)
            edit.setStyleSheet(f"background-color: {background};")
        if lines == self._last_lines:
            return
        self._last_lines = lines
        edit.setUpdatesEnabled(False)

        edit.setContextMenuPolicy(Qt.NoContextMenu)
        edit.setReadOnly(False)
        edit.clear()
        cursor = edit.textCursor()
        cursor.beginEditBlock()
        for i, runs in enumerate(lines):
            if i:
                cursor.insertBlock()
            for text, color in runs:
                cursor.insertText(text, self._char_format(color))
        cursor.endEditBlock()
        edit.verticalScrollBar().setValue(0)
        edit.setReadOnly(True)
        edit.setUpdatesEnabled(True)

    def _cell_at(self, pos):
        cursor = self.text.cursorForPosition(pos)
        col = cursor.positionInBlock()
        if pos.x() < self.text.cursorRect(cursor).left():
            col -= 1
        return max(col, 0), cursor.blockNumber()

    def eventFilter(self, obj, event):
        if obj is self.text and self._frame_styled:
            kind = event.type()
            if kind in KEY_EVENTS and not event.isAutoRepeat():
                self.frameKey.emit(event.key(), KEY_EVENTS[kind])
                return event.key() in CAMERA_KEYS
            if kind == QEvent.FocusOut:
                self.frameKey.emit(RELEASE_ALL, False)
        if obj is self.text.viewport() and self._frame_styled:
            if event.type() == QEvent.Wheel:
                col, row = self._cell_at(event.position().toPoint())
                self.frameWheel.emit(event.angleDelta().y(), col, row)
                return True
            kind = MOUSE_KINDS.get(event.type())
            if kind:
                if kind == "press":
                    self.text.setFocus()
                pos = event.position().toPoint()
                col, row = self._cell_at(pos)
                button = MOUSE_BUTTONS.get(event.button(), "")
                self.frameMouse.emit(kind, col, row, button, pos.x(), pos.y())
                return True
        return super().eventFilter(obj, event)

    def _char_format(self, color):
        fmt = self._frame_fmt.get(color)
        if fmt is None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            self._frame_fmt[color] = fmt
        return fmt

    def _release_frame_style(self):
        if self._frame_styled:
            self._frame_styled = False
            self._last_style = None
            self._last_lines = None
            self.text.setContextMenuPolicy(Qt.DefaultContextMenu)
            self.text.setStyleSheet("")
            self.text.setFont(mono(8))

    def set_pixmap(self, pix):
        self.label.setPixmap(pix)

    def pixmap(self):
        return self.label.pixmap()

    def clear_image(self):
        self.label.clear()

    def scroll_by(self, vertical, amount):
        target = self.scroll if self.scroll.isVisible() else self.text
        bar = target.verticalScrollBar() if vertical else target.horizontalScrollBar()
        bar.setValue(bar.value() + amount * SCROLL_STEP)

    def image_rect_in(self, ancestor):
        pix = self.label.pixmap()
        if not pix or pix.isNull() or not self.scroll.isVisible():
            return None
        offset = self.label.mapTo(ancestor, QPoint(0, 0))
        dx = max(0, (self.label.width() - pix.width()) // 2)
        dy = max(0, (self.label.height() - pix.height()) // 2)
        return offset.x() + dx, offset.y() + dy, pix.width(), pix.height()

    def update_icons(self, theme, muted):
        suffix = "_l" if theme == "Light" else ""
        self._set_icon(self.btn_clear, f"clear_ascii{suffix}.png", "Clear")
        if muted:
            self._set_icon(self.btn_mute, f"mute{suffix}.png", "Unmute")
        else:
            self._set_icon(self.btn_mute, f"unmute{suffix}.png", "Mute")

    @staticmethod
    def _set_icon(btn, filename, fallback_text):
        path = get_resource_path(filename)
        if os.path.exists(path):
            btn.setIcon(QIcon(path))
            btn.setText("")
            btn.setFixedSize(28, 20)
        else:
            btn.setIcon(QIcon())
            btn.setText(fallback_text)
            btn.setFixedSize(50, 20)

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QVBoxLayout, QWidget

HUE_MAX = 359


class _Hsv:
    def __init__(self):
        self.h, self.s, self.v = 0, 255, 255


class _Surface(QWidget):
    changed = Signal()
    released = Signal()

    def __init__(self, hsv):
        super().__init__()
        self.hsv = hsv
        self.setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        self._pick(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._pick(event)

    def mouseReleaseEvent(self, event):
        self.released.emit()

    def _pick(self, event):
        w = max(1, self.width() - 1)
        h = max(1, self.height() - 1)
        fx = min(max(event.position().x() / w, 0.0), 1.0)
        fy = min(max(event.position().y() / h, 0.0), 1.0)
        self._set(fx, fy)
        self.update()
        self.changed.emit()

    def _clip_rounded(self, painter):
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 4, 4)
        painter.setClipPath(path)

    @staticmethod
    def _ring(painter, center, radius=6):
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0, 160), 3))
        painter.drawEllipse(center, radius, radius)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(center, radius, radius)


class SaturationValueSquare(_Surface):
    def _set(self, fx, fy):
        self.hsv.s = int(fx * 255)
        self.hsv.v = int((1.0 - fy) * 255)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._clip_rounded(p)
        r = self.rect()

        across = QLinearGradient(r.left(), 0, r.right(), 0)
        across.setColorAt(0, Qt.white)
        across.setColorAt(1, QColor.fromHsv(self.hsv.h, 255, 255))
        p.fillRect(r, across)

        down = QLinearGradient(0, r.top(), 0, r.bottom())
        down.setColorAt(0, QColor(0, 0, 0, 0))
        down.setColorAt(1, Qt.black)
        p.fillRect(r, down)

        p.setClipping(False)
        x = self.hsv.s / 255 * (self.width() - 1)
        y = (1 - self.hsv.v / 255) * (self.height() - 1)
        self._ring(p, QPointF(x, y))


class HueBar(_Surface):
    def _set(self, fx, fy):
        self.hsv.h = min(HUE_MAX, int(fx * HUE_MAX))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._clip_rounded(p)
        r = self.rect()

        rainbow = QLinearGradient(r.left(), 0, r.right(), 0)
        for i in range(7):
            rainbow.setColorAt(i / 6, QColor.fromHsv(int(i * HUE_MAX / 6), 255, 255))
        p.fillRect(r, rainbow)

        p.setClipping(False)
        x = self.hsv.h / HUE_MAX * (self.width() - 1)
        self._ring(p, QPointF(x, self.height() / 2), radius=5)


class ColorPicker(QWidget):
    colorChanged = Signal(str)
    colorCommitted = Signal(str)

    def __init__(self, hex_color="#8AA090", parent=None):
        super().__init__(parent)
        self._hsv = _Hsv()

        self.square = SaturationValueSquare(self._hsv)
        self.square.setFixedHeight(72)
        self.hue = HueBar(self._hsv)
        self.hue.setFixedHeight(14)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 2)
        layout.setSpacing(6)
        layout.addWidget(self.square)
        layout.addWidget(self.hue)

        self.hue.changed.connect(self.square.update)
        for surface in (self.square, self.hue):
            surface.changed.connect(lambda: self.colorChanged.emit(self.color()))
            surface.released.connect(lambda: self.colorCommitted.emit(self.color()))

        self.set_color(hex_color)

    def color(self):
        return QColor.fromHsv(self._hsv.h, self._hsv.s, self._hsv.v).name().upper()

    def set_color(self, hex_color):
        c = QColor(hex_color)
        if not c.isValid():
            return
        if c.hsvHue() >= 0:
            self._hsv.h = c.hsvHue()
        self._hsv.s = c.hsvSaturation()
        self._hsv.v = c.value()
        self.square.update()
        self.hue.update()

import time

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from ui.widgets import mono


class LogConsole(QTextEdit):
    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.setObjectName("txt_logs")
        self.setFont(mono(8))
        self.setReadOnly(True)
        self.colors = colors
        self._last_was_progress = False

    def set_colors(self, colors):
        self.colors = colors

    def write(self, text, tag="info", progress=False):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.colors.get(f"log_{tag}", self.colors["log_info"])))
        line = f"[sys] {time.strftime('%H:%M:%S')}  {text}"

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        if progress:
            if self._last_was_progress:
                cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
            cursor.insertText(line, fmt)
        else:
            if self._last_was_progress:
                cursor.insertText("\n")
            cursor.insertText(line + "\n", fmt)

        self._last_was_progress = progress
        self.ensureCursorVisible()

from PySide6.QtCore import QObject, QTimer

from game.manager import GameStreamManager, client_origin
from ui.overlay import GameOverlayWindow

ENGAGE_RETRIES = 40
ENGAGE_RETRY_MS = 150
ENGAGE_DELAY_MS = 300
TICK_MS = 100


class GameControl(QObject):
    def __init__(self, window, preview, log, is_playing, on_game_closed):
        super().__init__(window)
        self.window = window
        self.preview = preview
        self.log = log
        self.is_playing = is_playing
        self.on_game_closed = on_game_closed

        self.manager = GameStreamManager(log_callback=log)
        self.overlay = GameOverlayWindow()
        self.active = False

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)

    def start_session(self, hwnd, title):
        self.manager.start_game_session(hwnd, title)
        QTimer.singleShot(ENGAGE_DELAY_MS, self.engage)

    def stop_session(self):
        self.disengage()
        self.manager.stop_game_session()

    def close(self):
        self.overlay.close()

    def viewer_rect(self):
        win = self.window
        if not self.is_playing() or win.isMinimized():
            return None
        local = self.preview.image_rect_in(win)
        if local is None:
            return None

        x, y, w, h = local
        dpr = win.devicePixelRatioF()
        ox, oy = client_origin(int(win.winId()))
        return (
            ox + int(round(x * dpr)),
            oy + int(round(y * dpr)),
            max(64, int(round(w * dpr))),
            max(64, int(round(h * dpr))),
        )

    def engage(self, attempts=0):
        if not self.is_playing() or self.active:
            return

        rect = self.viewer_rect()
        if rect is None:
            if attempts < ENGAGE_RETRIES:
                QTimer.singleShot(ENGAGE_RETRY_MS, lambda: self.engage(attempts + 1))
            else:
                self.log("Game control could not start: no stream frame was rendered.", "err")
            return

        if not self.manager.engage(int(self.window.winId()), rect):
            self.log("Game control could not start: game window is not available.", "err")
            return

        self.active = True
        self.overlay.set_frame(self.preview.pixmap())
        self._timer.start()
        self.log("Game control active. Keyboard and mouse go straight to the game through the stream view.", "info")
        self.log("Use the game in windowed mode (not exclusive fullscreen) for input to work.", "note")

    def disengage(self):
        self._timer.stop()
        self.overlay.hide_overlay()
        if self.active:
            self.active = False
            self.manager.disengage()

    def on_preview_click(self):
        if not self.is_playing():
            return
        if not self.active:
            self.engage()
        else:
            self.manager.focus_game()

    def push_frame(self, pix):
        if self.active and self.overlay.is_shown:
            self.overlay.set_frame(pix)

    def _tick(self):
        if not self.active:
            return
        if not self.is_playing() or not self.manager.game_alive():
            if self.is_playing():
                self.log("Game window closed.", "warn")
            self.on_game_closed()
            return

        rect = self.viewer_rect()
        if rect is None:
            self.overlay.hide_overlay()
            return

        self.manager.update_target(rect)
        if self.manager.game_has_focus():
            self.overlay.show_at(rect)
        else:
            self.overlay.hide_overlay()

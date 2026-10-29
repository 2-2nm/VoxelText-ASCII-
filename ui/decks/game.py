from game.capture import guess_game_window, list_active_windows
from ui.decks.base import ModeDeck
from ui.theme import DANGER_BUTTON_STYLE, MODE_ACCENTS, solid_button_style
from ui.widgets import FlatComboBox, badge, button, muted_label, row


class GameDeck(ModeDeck):
    KEY = "game"
    TITLE = "Game"
    MONOCHROME_HEX = "#E2E8F0"

    def _build_extras(self):
        self.combo_windows = FlatComboBox()
        self.combo_windows.setFixedHeight(22)
        self.btn_refresh = button("Refresh", height=22)

        self.lbl_fps = badge("0 FPS")

        self.btn_start = button("Start Stream", font=(8, True),
                                style=solid_button_style(MODE_ACCENTS["game"], "#08090C"))
        self.btn_stop = button("Stop Stream", font=(8, True), style=DANGER_BUTTON_STYLE)
        self.btn_stop.setEnabled(False)

    def _rows(self):
        return [
            self._style_row(),
            muted_label("// TARGET WINDOW & PARAMETERS"),
            row((self.combo_windows, 1), self.btn_refresh),
            *self._width_rows(),
            self._alpha_row(self.lbl_fps),
            row(self.btn_start, self.btn_stop),
        ]

    def set_streaming(self, active):
        self.btn_start.setEnabled(not active)
        self.btn_stop.setEnabled(active)
        if not active:
            self.set_fps(0)

    def set_fps(self, fps):
        self.lbl_fps.setText(f"{round(fps)} FPS")

    def selected(self):
        return self.combo_windows.currentData(), self.combo_windows.currentText()

    def refresh_windows(self, saved_title=""):
        combo = self.combo_windows
        prev_hwnd, prev_title = self.selected()
        windows = list_active_windows()

        combo.clear()
        if not windows:
            combo.addItem("No active game window found", None)
            return

        for hwnd, title in windows:
            combo.addItem(title, hwnd)

        guessed = guess_game_window(windows)
        lookups = (
            lambda: combo.findData(prev_hwnd) if prev_hwnd else -1,
            lambda: combo.findText(prev_title) if prev_title else -1,
            lambda: combo.findText(saved_title) if saved_title else -1,
            lambda: combo.findData(guessed) if guessed else -1,
        )
        idx = -1
        for lookup in lookups:
            idx = lookup()
            if idx >= 0:
                break
        if idx < 0:
            combo.insertItem(0, "Select a game window...", None)
            idx = 0

        combo.setCurrentIndex(idx)
        self.log.emit(f"Detected {len(windows)} active window targets.", "info")

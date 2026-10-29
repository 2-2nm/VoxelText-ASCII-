from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSlider

from ui.decks.base import ModeDeck
from ui.theme import DANGER_BUTTON_STYLE, contrast_text, solid_button_style
from ui.widgets import STRETCH, badge, button, labeled_row, muted_label, row

NO_TIME = "00:00 / 00:00"
RESUME_BG = "#C4A878"


def format_time(seconds):
    if seconds is None or seconds < 0:
        seconds = 0
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"


class VideoDeck(ModeDeck):
    KEY = "video"
    TITLE = "Video"
    MONOCHROME_HEX = "#E2E8F0"

    seekRequested = Signal(int)

    def _build_extras(self):
        self._playing = False
        self._paused = False
        self.user_seeking = False

        self.btn_save = button("Save as MP4", height=20, font=(8, True))

        self.lbl_time = badge(NO_TIME)
        self.slider_time = QSlider(Qt.Horizontal)
        self.slider_time.setRange(0, 1000)
        self.slider_time.sliderPressed.connect(self._begin_seek)
        self.slider_time.sliderReleased.connect(self._end_seek)

        self.btn_pause = button("Pause", font=(8, True))
        self.btn_pause.setEnabled(False)
        self.btn_stop = button("Stop", font=(8, True), style=DANGER_BUTTON_STYLE)
        self.btn_stop.setEnabled(False)

    def _rows(self):
        return [
            self._style_row(),
            row(muted_label("// PARAMETERS"), STRETCH, self.btn_save),
            *self._width_rows(),
            labeled_row("Timeline", self.lbl_time),
            self.slider_time,
            self._alpha_row(),
            row(self.btn_pause, self.btn_stop),
        ]

    def _begin_seek(self):
        self.user_seeking = True

    def _end_seek(self):
        self.seekRequested.emit(self.slider_time.value())
        self.user_seeking = False

    def set_time(self, current, total):
        if self.user_seeking:
            return
        if total > 0:
            self.slider_time.setMaximum(int(total))
            self.slider_time.setValue(min(int(current), int(total)))
        self.lbl_time.setText(f"{format_time(current)} / {format_time(total)}")

    def reset_time(self):
        self.lbl_time.setText(NO_TIME)
        self.slider_time.setValue(0)

    def set_playback(self, playing, paused=False):
        self._playing = playing
        self._paused = paused
        self.btn_pause.setEnabled(playing)
        self.btn_stop.setEnabled(playing)
        self._refresh_pause_button()

    def _refresh_pause_button(self):
        btn = self.btn_pause
        if not self._playing:
            btn.setText("Pause")
            btn.setStyleSheet("")
        elif self._paused:
            btn.setText("Resume")
            btn.setStyleSheet(solid_button_style(RESUME_BG, "#08090C"))
        else:
            accent = self._colors["accent"]
            btn.setText("Pause")
            btn.setStyleSheet(solid_button_style(accent, contrast_text(accent)))

    def apply_theme(self, colors, theme):
        super().apply_theme(colors, theme)
        self._refresh_pause_button()

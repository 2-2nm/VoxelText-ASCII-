from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider

from ui.decks.base import ModeDeck
from ui.widgets import badge, button, labeled_row, muted_label


class ImageDeck(ModeDeck):
    KEY = "photo"
    TITLE = "Image"
    WIDTH_MAX = 200

    def _build_extras(self):
        self.lbl_thresh = badge("30%")
        self.slider_cutoff = QSlider(Qt.Horizontal)
        self.slider_cutoff.setRange(0, 100)
        self.slider_cutoff.setValue(30)
        self.slider_cutoff.valueChanged.connect(lambda v: self.lbl_thresh.setText(f"{v}%"))

        self.btn_save = button("Save as PNG", font=(9, True), height=24)

    def _rows(self):
        return [
            self._style_row(),
            muted_label("// PARAMETERS"),
            *self._width_rows(),
            labeled_row("Cutoff", self.lbl_thresh),
            self.slider_cutoff,
            self._alpha_row(),
            self.btn_save,
        ]

    @property
    def cutoff(self):
        return round(self.slider_cutoff.value())

    def load_state(self, s):
        super().load_state(s)
        cutoff = int(s["photo_cutoff"])
        self.slider_cutoff.setValue(cutoff)
        self.lbl_thresh.setText(f"{cutoff}%")

    def get_state(self):
        return {**super().get_state(), "photo_cutoff": self.cutoff}

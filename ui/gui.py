import os
import platform

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QSplitter, QVBoxLayout, QWidget,
)

from core.ascii import get_charset, set_charset
from core.utils import MAX_WORKERS, get_resource_path
from game.player import GPUAsciiGamePlayer
from video.audio import AudioPlayer
from video.player import GPUAsciiVideoPlayer

from ui.console import LogConsole
from ui.decks import GameDeck, ImageDeck, VideoDeck, VoxelDeck
from ui.dialogs import IMAGE_FILTER, MP4_FILTER, PNG_FILTER, TEXT_FILTER, VIDEO_FILTER, open_file, save_file
from ui.export import save_photo
from ui.afetch import render_afetch
from ui.game_control import GameControl
from ui.preview import PreviewPane, pil_to_qpixmap
from ui.settings import load_settings, save_settings
from ui.theme import MODE_ACCENTS, THEMES, build_stylesheet, contrast_text, top_button_style
from ui.widgets import STRETCH, SegmentedButton, add_all, button, column, mono, muted_label, row
from ui.workers import SignalBridge, spawn, start_image_render, start_video_export

try:
    import pywinstyles
except ImportError:
    pywinstyles = None

DECK_KEYS = {"Image": "photo", "Video": "video", "Game": "game", "Voxel": "voxel"}
DECK_TITLES = {
    "photo": "Image Settings",
    "video": "Video Settings",
    "game": "Game Stream Settings",
    "voxel": "Voxel Settings",
}
MIN_DECK_HEIGHT = 140
SCROLL_KEYS = (
    (Qt.Key_Up, True, -3), (Qt.Key_Down, True, 3), (Qt.Key_Left, False, -3), (Qt.Key_Right, False, 3),
)


class AsciiArtAppPySide6(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoxelText")

        self.settings = load_settings()
        set_charset(self.settings["ascii_charset"])
        self.current_theme = self.settings["theme"] if self.settings["theme"] in THEMES else "Dark"
        self.colors = THEMES[self.current_theme]

        self.last_image_path = None
        self.last_save_path = None
        self.last_converted_basename = ""
        self.current_ascii_text = ""
        self.current_gui_preview = None
        self.current_pil_img = None
        self.preview_video_path = None
        self.is_video_playing = False
        self.is_video_paused = False
        self.active_video_player = None
        self.is_game_playing = False
        self.active_game_player = None
        self._latest_game_img = None
        self._game_frame_inflight = False
        self.audio_player = AudioPlayer()
        self.cached_container_w = 800
        self.cached_container_h = 600
        self.is_fullscreen = False
        self._splitter_ready = False

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._refresh_image)

        self.signals = SignalBridge()
        self._build_ui()
        self._connect_signals()
        self.game = GameControl(
            self, self.preview, self.append_system_log,
            is_playing=lambda: self.is_game_playing,
            on_game_closed=self.stop_game_stream,
        )

        self.resize(1500, 840)
        self.setMinimumSize(920, 620)
        self._center_window()
        icon_path = get_resource_path("app-icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self._apply_loaded_settings()
        self._show_afetch()
        self.append_system_log(f"Engine initialized. Multi-Core Active ({MAX_WORKERS} Threads).", "info")

    def _build_ui(self):
        central = QWidget(self)
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self.preview = PreviewPane()
        self.decks = {
            "photo": ImageDeck(self.settings, self.colors, self.current_theme),
            "video": VideoDeck(self.settings, self.colors, self.current_theme),
            "game": GameDeck(self.settings, self.colors, self.current_theme),
            "voxel": VoxelDeck(self.settings, self.colors, self.current_theme),
        }
        self.console = LogConsole(self.colors)

        layout.addWidget(self._build_topbar())

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.preview)
        self.splitter.addWidget(self._build_bottom_deck())
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        layout.addWidget(self.splitter)

    def _build_topbar(self):
        bar = QFrame()
        bar.setObjectName("surface")
        bar.setFixedHeight(48)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)

        title = QLabel("VoxelText")
        title.setFont(QFont("Georgia", 16, QFont.Normal, True))

        self.btn_top_game = button("Play Game", lambda: self.start_game_stream_process(), size=(98, 32))
        self.btn_top_video = button("Video", lambda: self.convert_video_process(), size=(88, 32))
        self.btn_top_load = button("Image", lambda: self.convert_image_process(), size=(88, 32))

        self.switch_theme = QCheckBox("DARK")
        self.switch_theme.setFont(mono(9, True))
        self.switch_theme.clicked.connect(self.toggle_theme_mode)

        add_all(layout, [title, muted_label("- by 2.2nm", 11), STRETCH,
                         self.btn_top_game, self.btn_top_video, self.btn_top_load, self.switch_theme])
        return bar

    def _build_bottom_deck(self):
        self.bd = QFrame()
        self.bd.setObjectName("surface")
        self.bd.setMinimumHeight(MIN_DECK_HEIGHT)
        layout = QHBoxLayout(self.bd)
        layout.setContentsMargins(10, 8, 10, 8)

        self.seg_deck_mode = SegmentedButton(list(DECK_KEYS), default="Image")
        self.seg_deck_mode.valueChanged.connect(self.switch_deck_mode)
        deck_area = column(row(self.seg_deck_mode, STRETCH), row(*self.decks.values()))

        btn_close = button("×", self.hide_bottom_deck, size=(20, 20), font=(10, True))
        btn_close.setObjectName("btnCloseDeck")
        console_area = column(row(muted_label("// CONSOLE LOGS"), STRETCH, btn_close), self.console)

        layout.addWidget(deck_area, stretch=2)
        layout.addWidget(console_area, stretch=1)
        return self.bd

    def _connect_signals(self):
        s = self.signals
        s.log_signal.connect(self._on_log)
        s.video_frame_signal.connect(self._on_video_frame)
        s.video_time_signal.connect(self._on_video_time)
        s.video_finished_signal.connect(self._on_video_finished)
        s.game_fps_signal.connect(self._on_game_fps)
        s.image_render_success_signal.connect(self._on_image_render_success)
        s.image_render_error_signal.connect(self._on_image_render_error)
        s.video_export_progress_signal.connect(self._on_video_export_progress)
        s.video_export_success_signal.connect(self._on_video_export_success)
        s.video_export_error_signal.connect(self._on_video_export_error)

        p = self.preview
        p.sizeChanged.connect(self._on_preview_resized)
        p.btn_toggle_deck.clicked.connect(self.toggle_bottom_deck)
        p.btn_clear.clicked.connect(self.clear_ascii_process)
        p.btn_mute.clicked.connect(self.toggle_video_mute)
        p.label.clicked.connect(lambda: self.game.on_preview_click())

        photo, video, game, voxel = (self.decks[k] for k in ("photo", "video", "game", "voxel"))
        for name, deck in self.decks.items():
            if hasattr(deck, "log"):
                deck.log.connect(self.append_system_log)
            if hasattr(deck, "charsetChanged"):
                deck.charsetChanged.connect(self._on_charset_changed)

        photo.colorModeChanged.connect(lambda _: self._refresh_image())
        photo.styleChanged.connect(lambda _: self._refresh_image())
        photo.transparencyChanged.connect(lambda _: self._refresh_image())
        photo.btn_save.clicked.connect(self.save_as_photo_process)

        video.styleChanged.connect(lambda v: self.append_system_log(f"Video style switched to {v}.", "info"))
        video.btn_save.clicked.connect(self.save_as_video_process)
        video.btn_pause.clicked.connect(self.toggle_video_pause)
        video.btn_stop.clicked.connect(self.stop_video_playback)
        video.seekRequested.connect(self._on_seek_requested)

        game.styleChanged.connect(lambda v: self.append_system_log(f"Game ASCII style switched to {v}.", "info"))
        game.btn_refresh.clicked.connect(lambda: game.refresh_windows(self.settings.get("game_window_title", "")))
        game.btn_start.clicked.connect(lambda: self.start_game_stream_process())
        game.btn_stop.clicked.connect(self.stop_game_stream)

        voxel.styleChanged.connect(lambda v: self.append_system_log(f"Voxel ASCII style switched to {v}.", "info"))
        voxel.tick.connect(self._on_voxel_tick)
        p.frameMouse.connect(voxel.handle_mouse)
        p.frameWheel.connect(voxel.handle_wheel)
        p.frameKey.connect(voxel.handle_key)

    def _apply_theme(self):
        self.colors = THEMES[self.current_theme]
        c = self.colors
        accent = c["accent"]

        self.setStyleSheet(build_stylesheet(c, self.current_theme))
        for btn, bg, fg, hover in (
            (self.btn_top_load, accent, contrast_text(accent), "#8B919E"),
            (self.btn_top_video, MODE_ACCENTS["video"], "#000000", "#6E8A74"),
            (self.btn_top_game, MODE_ACCENTS["game"], "#08090C", "#A3895B"),
        ):
            btn.setStyleSheet(top_button_style(bg, fg, hover))

        self.seg_deck_mode.set_colors(accent, c["bg_panel"], contrast_text(accent), c["text_primary"])
        for deck in self.decks.values():
            if hasattr(deck, "apply_theme"):
                deck.apply_theme(c, self.current_theme)
        self.console.set_colors(c)
        self.preview.update_icons(self.current_theme, self.audio_player.is_muted)

        is_dark = self.current_theme == "Dark"
        self.switch_theme.setChecked(is_dark)
        self.switch_theme.setText("DARK" if is_dark else "LIGHT")

        if pywinstyles and platform.system() == "Windows":
            try:
                pywinstyles.change_header_color(self, color=c["bg_dark"])
            except Exception:
                pass

    def _apply_loaded_settings(self):
        self._apply_theme()
        mode = self.settings["deck_mode"] if self.settings["deck_mode"] in DECK_KEYS else "Image"
        self.seg_deck_mode.set(mode)
        self.switch_deck_mode(mode)
        for deck in self.decks.values():
            if hasattr(deck, "load_state"):
                deck.load_state(self.settings)

    def _collect_settings(self):
        deck_h = self.settings.get("deck_height", 180)
        if self.bd.isVisible():
            sizes = self.splitter.sizes()
            if len(sizes) > 1 and sizes[1] >= 110:
                deck_h = sizes[1]

        hwnd, title = self.decks["game"].selected()
        state = {
            "game_window_title": title if hwnd else self.settings.get("game_window_title", ""),
            "theme": self.current_theme,
            "ascii_charset": get_charset(),
            "deck_mode": self.seg_deck_mode.get(),
            "deck_height": max(MIN_DECK_HEIGHT, deck_h),
        }
        for deck in self.decks.values():
            if hasattr(deck, "get_state"):
                state.update(deck.get_state())
        return state

    def toggle_theme_mode(self):
        self.current_theme = "Dark" if self.switch_theme.isChecked() else "Light"
        self._apply_theme()

        if self.is_video_playing or self.is_game_playing:
            pass
        elif self.last_image_path and self.preview.image_visible:
            self._refresh_image()
        else:
            self._show_afetch()
        self.append_system_log(f"Session theme switched to {self.current_theme}.", "info")

    def showEvent(self, event):
        super().showEvent(event)
        if not self._splitter_ready:
            self._splitter_ready = True
            height = max(MIN_DECK_HEIGHT, self.settings.get("deck_height", 180))
            QTimer.singleShot(0, lambda: self.splitter.setSizes([10000, height]))

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_F11:
            self.toggle_fullscreen()
        elif key == Qt.Key_Escape:
            self.exit_fullscreen()
        else:
            for scroll_key, vertical, amount in SCROLL_KEYS:
                if key == scroll_key:
                    self.preview.scroll_by(vertical, amount)
                    return
            super().keyPressEvent(event)

    def closeEvent(self, event):
        save_settings(self._collect_settings())
        self.stop_video_playback()
        self.stop_game_stream()
        self.decks["voxel"].stop_render()
        self.game.close()
        event.accept()

    def _center_window(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.is_fullscreen = True
            self.showFullScreen()

    def exit_fullscreen(self):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.showNormal()

    def _on_preview_resized(self, w, h):
        if w <= 50 or h <= 50:
            return
        changed = abs(self.cached_container_w - w) > 5 or abs(self.cached_container_h - h) > 5
        self.cached_container_w, self.cached_container_h = w, h
        if changed and self.last_image_path:
            self._resize_timer.start(100)

    def switch_deck_mode(self, value):
        key = DECK_KEYS.get(value, "photo")
        for name, deck in self.decks.items():
            deck.setVisible(name == key)

        if key == "voxel":
            self.stop_video_playback()
            self.stop_game_stream()
            self.decks["voxel"].start_render()
        elif self.decks["voxel"].is_running():
            self.decks["voxel"].stop_render()
            if not (self.is_video_playing or self.is_game_playing):
                self._restore_preview()

        if key == "game":
            self.decks["game"].refresh_windows(self.settings.get("game_window_title", ""))
            
        self.append_system_log(f"Settings deck switched to {DECK_TITLES[key]}.", "info")

    def _set_deck_visible(self, visible, message):
        self.bd.setVisible(visible)
        self.preview.btn_toggle_deck.setText("Hide Settings" if visible else "Show Settings")
        self.append_system_log(message, "info")

    def toggle_bottom_deck(self):
        if self.bd.isVisible():
            self._set_deck_visible(False, "Settings deck hidden.")
        else:
            self._set_deck_visible(True, "Settings deck displayed.")
            height = max(MIN_DECK_HEIGHT, self.settings.get("deck_height", 180))
            self.splitter.setSizes([10000, height])
        QTimer.singleShot(50, self._refresh_image)

    def hide_bottom_deck(self):
        if self.bd.isVisible():
            self._set_deck_visible(False, "Settings deck closed.")

    def _on_charset_changed(self, name):
        if not name or name == get_charset():
            return
        set_charset(name)
        for deck in self.decks.values():
            if hasattr(deck, "set_charset"):
                deck.set_charset(name)
        self.append_system_log(f"ASCII charset switched to {name}.", "info")
        self._refresh_image()

    def append_system_log(self, text, tag="info", is_progress=False):
        self.signals.log_signal.emit(text, tag, is_progress)

    @Slot(str, str, bool)
    def _on_log(self, text, tag, is_progress):
        self.console.write(text, tag, is_progress)

    def _show_afetch(self):
        self.preview.show_text()
        render_afetch(self.preview.text, self.colors, self.current_theme)

    def clear_ascii_process(self):
        self.stop_video_playback()
        self.stop_game_stream()
        self.decks["voxel"].stop_render()
        self.current_ascii_text = ""
        self.current_gui_preview = None
        self.current_pil_img = None
        self.last_converted_basename = ""
        self.preview.clear_image()
        self.decks["video"].reset_time()
        self._show_afetch()
        self.append_system_log("ASCII preview cleared.", "info")

    def _preview_info(self, key):
        cols = max(20, self.decks[key].target_cols())
        return cols, max(100, self.cached_container_w - 32), max(100, self.cached_container_h - 72)

    def _on_voxel_tick(self):
        deck = self.decks["voxel"]
        font, cols, rows, aspect = self.preview.frame_grid(deck.target_cols())
        self.preview.show_frame(deck.frame(cols, rows, aspect), font, deck.background)

    def _restore_preview(self):
        if self.last_image_path:
            self.convert_image_process(skip_dialog=True)
        else:
            self._show_afetch()

    def _refresh_image(self):
        if self.decks["voxel"].is_running():
            return
        if self.last_image_path and not self.is_video_playing and not self.is_game_playing:
            self.convert_image_process(skip_dialog=True)

    def convert_image_process(self, skip_dialog=False):
        self.stop_video_playback()
        self.stop_game_stream()
        self.decks["voxel"].stop_render()

        if not skip_dialog or not self.last_image_path:
            path = open_file(self, "Select Source Image", IMAGE_FILTER)
            if not path:
                self.append_system_log("Process aborted by user.", "warn")
                return
            self.last_image_path = path
            self.last_converted_basename = os.path.splitext(os.path.basename(path))[0]

            save_path = save_file(self, "Save ASCII Output...", f"{self.last_converted_basename}_ascii.txt", TEXT_FILTER)
            if not save_path:
                self.append_system_log("Export directory selection cancelled.", "warn")
                return
            self.last_save_path = save_path
        else:
            path = self.last_image_path
            save_path = self.last_save_path or "temp_ascii.txt"

        deck = self.decks["photo"]
        cols = deck.target_cols(self.append_system_log)
        mode, palette_hex = deck.render_color(self.current_theme)
        self.btn_top_load.setEnabled(False)
        self.append_system_log(
            f"Rendering GPU Image ASCII... [W: {cols}px, Style: {deck.fullcolor_style}, Cutoff: {deck.cutoff}%]", "info")

        start_image_render(
            self.signals,
            path=path,
            save_path=save_path,
            cols=cols,
            max_w=max(100, self.cached_container_w - 32),
            max_h=max(100, self.cached_container_h - 72),
            mode=mode,
            style=deck.fullcolor_style,
            palette_hex=palette_hex,
            transparency=deck.transparency,
            bg_color=self.colors["bg_surface"],
        )

    @Slot(object, str, str)
    def _on_image_render_success(self, pil_img, text, save_path):
        self.current_ascii_text = text
        self.current_pil_img = pil_img
        self.append_system_log(f"Render output written to: {os.path.basename(save_path)}", "info")

        self.preview.show_image()
        self.preview.set_pixmap(pil_to_qpixmap(pil_img))
        self.btn_top_load.setEnabled(True)
        self.append_system_log("GPU Image preview rendering completed smoothly.", "info")

    @Slot(str)
    def _on_image_render_error(self, message):
        self.append_system_log(f"Render Error: {message}", "err")
        QMessageBox.critical(self, "Terminal Error", f"Process failed:\n{message}")
        self.btn_top_load.setEnabled(True)

    def save_as_photo_process(self):
        if not self.current_ascii_text and not self.current_pil_img:
            self.append_system_log("Save PNG cancelled: No ASCII data present.", "warn")
            return

        default = f"{self.last_converted_basename}_ascii.png" if self.last_converted_basename else "ascii_photo.png"
        path = save_file(self, "Save ASCII as PNG...", default, PNG_FILTER)
        if not path:
            self.append_system_log("Save PNG cancelled by user.", "warn")
            return

        deck = self.decks["photo"]
        mode, palette_hex = deck.render_color(self.current_theme)
        try:
            save_photo(
                path,
                mode=mode,
                palette_hex=palette_hex,
                source_path=self.last_image_path,
                cols=deck.target_cols(self.append_system_log),
                style=deck.fullcolor_style,
                transparency=deck.transparency,
                bg_color=self.colors["bg_surface"],
                ascii_text=self.current_ascii_text,
                gui_preview=self.current_gui_preview,
            )
            self.append_system_log(f"High-res photo exported to: {os.path.basename(path)}", "info")
        except Exception as e:
            self.append_system_log(f"Save PNG error: {e}", "err")
            QMessageBox.critical(self, "Error", f"Failed:\n{e}")

    def _player_kwargs(self, key):
        deck = self.decks[key]
        mode, palette_hex = deck.render_color(self.current_theme)
        return dict(
            width_provider_fn=lambda: self._preview_info(key),
            style_provider_fn=lambda: deck.fullcolor_style,
            color_mode_provider_fn=lambda: deck.render_color(self.current_theme)[0],
            palette_hex_provider_fn=lambda: deck.render_color(self.current_theme)[1],
            transparency_provider_fn=lambda: deck.transparency,
            transparent_target=deck.transparency,
            color_mode=mode,
            palette_hex=palette_hex,
            fullcolor_style=deck.fullcolor_style,
            theme_bg_color=self.colors["bg_surface"],
        )

    def convert_video_process(self):
        self.stop_game_stream()
        self.decks["voxel"].stop_render()
        try:
            import cv2, moderngl
        except ImportError as e:
            self.append_system_log(f"Video conversion requires OpenCV and ModernGL ({e}).", "err")
            QMessageBox.critical(self, "Dependency Missing",
                                 "Please install dependencies:\n\npip install opencv-python moderngl")
            return

        path = open_file(self, "Select Source Video", VIDEO_FILTER)
        if not path:
            self.append_system_log("Video process aborted by user.", "warn")
            return

        self.stop_video_playback()
        self.preview_video_path = path
        self.last_converted_basename = os.path.splitext(os.path.basename(path))[0]
        self.append_system_log(
            f"Target video loaded for Internal GPU Offscreen Render: {os.path.basename(path)}", "info")

        kwargs = self._player_kwargs("video")
        self.is_video_playing = True
        self.is_video_paused = False
        self.btn_top_video.setEnabled(False)
        self.decks["video"].set_playback(True)

        has_audio, audio_msg = self.audio_player.load_audio_from_video(path)
        if not has_audio:
            self.append_system_log(f"Audio Disabled: {audio_msg}", "warn")

        self.preview.show_image()
        spawn(lambda: self._run_video(path, kwargs))

    def _run_video(self, path, kwargs):
        try:
            self.active_video_player = GPUAsciiVideoPlayer(
                video_path=path,
                audio_player=self.audio_player,
                update_ui_cb=lambda img: self.signals.video_frame_signal.emit(img),
                update_time_cb=lambda cur, tot: self.signals.video_time_signal.emit(cur, tot),
                **kwargs,
            )
            self.active_video_player.run(
                is_playing_flag_fn=lambda: self.is_video_playing,
                is_paused_flag_fn=lambda: self.is_video_paused,
            )
        except Exception as e:
            self.append_system_log(f"GPU Render Error: {e}", "err")
        finally:
            self.active_video_player = None
            self.is_video_playing = False
            self.is_video_paused = False
            self.signals.video_finished_signal.emit()

    def toggle_video_pause(self):
        if not self.is_video_playing:
            return
        self.is_video_paused = not self.is_video_paused
        self.decks["video"].set_playback(True, self.is_video_paused)
        if self.is_video_paused:
            self.audio_player.pause()
            self.append_system_log("Video playback paused.", "warn")
        else:
            self.audio_player.resume()
            self.append_system_log("Video playback resumed.", "info")

    def toggle_video_mute(self):
        muted = self.audio_player.toggle_mute()
        self.preview.update_icons(self.current_theme, muted)
        self.append_system_log("Audio muted." if muted else "Audio unmuted.", "warn" if muted else "info")

    def stop_video_playback(self):
        if not self.is_video_playing:
            return
        self.is_video_playing = False
        self.is_video_paused = False
        self.active_video_player = None
        self.audio_player.stop()

        self.decks["video"].set_playback(False)
        self.decks["video"].reset_time()
        self.btn_top_video.setEnabled(True)
        self.append_system_log("Video playback stopped.", "warn")

    def _on_seek_requested(self, seconds):
        if self.active_video_player:
            self.active_video_player.seek(seconds)

    @Slot(float, float)
    def _on_video_time(self, current, total):
        self.decks["video"].set_time(current, total)

    @Slot()
    def _on_video_finished(self):
        self.btn_top_video.setEnabled(True)
        self.decks["video"].set_playback(False)
        self.decks["video"].reset_time()
        self.append_system_log("GPU Video playback finished.", "info")

    @Slot(object)
    def _on_video_frame(self, pil_img):
        if self.is_game_playing:
            self._game_frame_inflight = False
            if self._latest_game_img is not None:
                pil_img = self._latest_game_img
        elif not self.is_video_playing:
            return
        pix = pil_to_qpixmap(pil_img)
        self.preview.set_pixmap(pix)
        self.game.push_frame(pix)

    def save_as_video_process(self):
        self.stop_video_playback()

        source = self.preview_video_path
        if not source or not os.path.exists(source):
            source = open_file(self, "Select Source Video for Export", VIDEO_FILTER)
            if not source:
                self.append_system_log("Video export cancelled: No source video selected.", "warn")
                return

        default = f"{os.path.splitext(os.path.basename(source))[0]}_ascii.mp4"
        output = save_file(self, "Save ASCII Video as MP4...", default, MP4_FILTER)
        if not output:
            self.append_system_log("Video export cancelled by user.", "warn")
            return

        deck = self.decks["video"]
        cols = deck.target_cols(self.append_system_log)
        mode, palette_hex = deck.render_color(self.current_theme)
        deck.btn_save.setEnabled(False)
        self.append_system_log(
            f"Starting MP4 Export Thread... [W: {cols}px, Mode: {deck.color_mode}, "
            f"Style: {deck.fullcolor_style}, Alpha: {deck.transparency}]", "info")

        start_video_export(
            self.signals,
            video_path=source,
            output_path=output,
            cols=cols,
            mode=mode,
            palette_hex=palette_hex,
            style=deck.fullcolor_style,
            transparency=deck.transparency,
            bg_color=self.colors["bg_surface"],
        )

    @Slot(int, int, str)
    def _on_video_export_progress(self, current, total, msg):
        pct = int(current / total * 100) if total > 0 else 0
        filled = pct * 20 // 100
        bar = "#" * filled + "-" * (20 - filled)
        self.append_system_log(f"Exporting MP4: [{bar}] {pct}% ({current}/{total})", "info", is_progress=True)

    @Slot(str)
    def _on_video_export_success(self, path):
        self.decks["video"].btn_save.setEnabled(True)
        self.append_system_log(f"Video MP4 Export Completed: {os.path.basename(path)}", "info")
        QMessageBox.information(self, "Export Success", f"ASCII Video saved successfully to:\n{path}")

    @Slot(str)
    def _on_video_export_error(self, message):
        self.decks["video"].btn_save.setEnabled(True)
        self.append_system_log(f"Video Export Error: {message}", "err")
        QMessageBox.critical(self, "Export Error", f"Failed to export video:\n{message}")

    def start_game_stream_process(self):
        self.stop_video_playback()
        self.stop_game_stream()
        self.decks["voxel"].stop_render()

        deck = self.decks["game"]
        self.seg_deck_mode.set("Game")
        self.switch_deck_mode("Game")

        hwnd, title = deck.selected()
        if not hwnd:
            deck.refresh_windows(self.settings.get("game_window_title", ""))
            hwnd, title = deck.selected()
        if not hwnd:
            QMessageBox.warning(self, "No Game Window",
                                "Please launch your game (e.g. Minecraft) and select its window target!")
            return

        self.is_game_playing = True
        deck.set_streaming(True)
        self.btn_top_game.setEnabled(False)
        self.preview.show_image()

        kwargs = self._player_kwargs("game")
        self.game.start_session(hwnd, title)
        self.append_system_log(f"Starting Real-Time ASCII Game Stream on Target: [{title}]", "info")
        spawn(lambda: self._run_game(hwnd, kwargs))

    def _run_game(self, hwnd, kwargs):
        try:
            self.active_game_player = GPUAsciiGamePlayer(
                hwnd=hwnd,
                update_ui_cb=self._push_game_frame,
                update_fps_cb=lambda fps: self.signals.game_fps_signal.emit(fps),
                log_cb=lambda text, tag="info": self.append_system_log(text, tag),
                **kwargs,
            )
            self.active_game_player.run(is_playing_flag_fn=lambda: self.is_game_playing)
        except Exception as e:
            self.append_system_log(f"Game Stream Error: {e}", "err")
        finally:
            self.active_game_player = None
            self.is_game_playing = False

    def _push_game_frame(self, img):
        self._latest_game_img = img
        if self._game_frame_inflight:
            return
        self._game_frame_inflight = True
        self.signals.video_frame_signal.emit(img)

    def stop_game_stream(self):
        if not (self.is_game_playing or self.game.active):
            return
        self.is_game_playing = False
        self.active_game_player = None
        self.game.stop_session()
        self.decks["game"].set_streaming(False)
        self.btn_top_game.setEnabled(True)
        self.append_system_log("Game ASCII Stream Stopped.", "warn")

    @Slot(float)
    def _on_game_fps(self, fps):
        self.decks["game"].set_fps(fps)
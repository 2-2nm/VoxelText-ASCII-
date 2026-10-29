import threading

from PySide6.QtCore import QObject, Signal

from core.ascii import render_image_gpu


class SignalBridge(QObject):
    log_signal = Signal(str, str, bool)
    video_frame_signal = Signal(object)
    video_time_signal = Signal(float, float)
    video_finished_signal = Signal()
    game_fps_signal = Signal(float)
    image_render_success_signal = Signal(object, str, str)
    image_render_error_signal = Signal(str)
    video_export_progress_signal = Signal(int, int, str)
    video_export_success_signal = Signal(str)
    video_export_error_signal = Signal(str)


def spawn(target):
    threading.Thread(target=target, daemon=True).start()


def start_image_render(signals, *, path, save_path, cols, max_w, max_h, mode, style,
                       palette_hex, transparency, bg_color):
    def job():
        try:
            pil_img, text = render_image_gpu(
                image_path=path,
                target_cols=cols,
                max_ui_w=max_w,
                max_ui_h=max_h,
                color_mode=mode,
                fullcolor_style=style,
                palette_hex=palette_hex,
                transparent_target=transparency,
                theme_bg_color=bg_color,
            )
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(text)
            signals.image_render_success_signal.emit(pil_img, text, save_path)
        except Exception as e:
            signals.image_render_error_signal.emit(str(e))

    spawn(job)


def start_video_export(signals, *, video_path, output_path, cols, mode, palette_hex, style, transparency, bg_color):
    def job():
        try:
            from video.exporter import export_ascii_video
            export_ascii_video(
                video_path=video_path,
                output_path=output_path,
                target_cols=cols,
                color_mode=mode,
                palette_hex=palette_hex,
                fullcolor_style=style,
                transparent_target=transparency,
                theme_bg_color=bg_color,
                progress_cb=lambda cur, tot, msg: signals.video_export_progress_signal.emit(cur, tot, msg),
            )
            signals.video_export_success_signal.emit(output_path)
        except Exception as e:
            signals.video_export_error_signal.emit(str(e))

    spawn(job)

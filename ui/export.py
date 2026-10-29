import os

from PIL import Image

from core.ascii import render_image_gpu, save_ascii_as_image

MIN_EXPORT_WIDTH = 2560


def upscale_to_min_width(img, min_width=MIN_EXPORT_WIDTH):
    if 0 < img.width < min_width:
        scale = min_width / img.width
        return img.resize((int(img.width * scale), int(img.height * scale)), Image.Resampling.NEAREST)
    return img


def save_photo(path, *, mode, palette_hex, source_path, cols, style, transparency, bg_color,
               ascii_text, gui_preview):
    if mode == "Color" and source_path:
        img, _ = render_image_gpu(
            image_path=source_path,
            target_cols=cols,
            max_ui_w=3840,
            max_ui_h=2160,
            color_mode="Color",
            fullcolor_style=style,
            palette_hex=palette_hex,
            transparent_target=transparency,
            theme_bg_color=bg_color,
        )
        upscale_to_min_width(img).save(path)
        return

    save_ascii_as_image(
        ascii_content=ascii_text,
        output_path=path,
        bg_color=bg_color,
        text_color=palette_hex,
        gui_preview_data=gui_preview if mode == "Color" else None,
    )
    if os.path.exists(path):
        with Image.open(path) as saved:
            saved.load()
            upscaled = upscale_to_min_width(saved)
        if upscaled is not saved:
            upscaled.save(path)

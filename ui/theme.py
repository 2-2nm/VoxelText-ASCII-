from typing import NamedTuple

DANGER = "#C47A7A"
DEFAULT_RENDER_HEX = "#8AA090"

THEMES = {
    "Dark": {
        "bg_dark": "#08090C",
        "bg_surface": "#101217",
        "bg_panel": "#1C2028",
        "text_primary": "#E6E8EE",
        "text_muted": "#8B919E",
        "accent": "#D5DBE6",
        "cmd_prompt": "#8AA090",
        "title_tag": "#E6E8EE",
        "key_tag": "#8B919E",
        "val_tag": "#E6E8EE",
        "note_tag": "#C4A878",
        "log_info": "#8AA090",
        "log_warn": "#C4A878",
        "log_err": "#C47A7A",
    },
    "Light": {
        "bg_dark": "#ECE8E1",
        "bg_surface": "#F7F4EE",
        "bg_panel": "#E4DFD6",
        "text_primary": "#16161A",
        "text_muted": "#5C5A56",
        "accent": "#1C1E24",
        "cmd_prompt": "#2F6B4A",
        "title_tag": "#16161A",
        "key_tag": "#5C5A56",
        "val_tag": "#16161A",
        "note_tag": "#9A6700",
        "log_info": "#2F6B4A",
        "log_warn": "#9A6700",
        "log_err": "#B42318",
    },
}


class PaletteEntry(NamedTuple):
    label: str
    value: str
    dark: str
    light: str

    def hex(self, theme):
        return self.light if theme == "Light" else self.dark


PALETTE = [
    PaletteEntry("Full Color", "Color", "#C8B8A4", "#8A6A4A"),
    PaletteEntry("Monochrome", "White", "#D5DBE6", "#1C1E24"),
]

LEGACY_COLORS = {
    "Green": "#8AA090", "Red": "#FF0000", "Pink": "#C48A96", "Coral": "#C47A7A",
    "Amber": "#C4A878", "Lime": "#9AB888", "Cyan": "#8EB4C4", "Violet": "#A99AB8",
    "Blue": "#8AA0C4", "Orange": "#C49678",
}

MODE_ACCENTS = {"photo": None, "video": "#8AA090", "game": "#C4A878", "voxel": "#8AA0C4"}


def render_hex(value, theme):
    if value != "Color":
        for entry in PALETTE:
            if entry.value == value:
                return entry.hex(theme)
    return DEFAULT_RENDER_HEX


def contrast_text(bg_hex):
    r, g, b = (int(bg_hex[i:i + 2], 16) for i in (1, 3, 5))
    return "#08090C" if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.55 else "#FFFFFF"


def _rgba(hex_color, alpha):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alpha})"


def blend(a_hex, b_hex, t):
    a = [int(a_hex[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b_hex[i:i + 2], 16) for i in (1, 3, 5)]
    r, g, bl = (round(x + (y - x) * t) for x, y in zip(a, b))
    return f"#{r:02X}{g:02X}{bl:02X}"


def solid_button_style(bg, fg, radius=4):
    return f"background-color: {bg}; color: {fg}; font-weight: bold; border-radius: {radius}px;"


DANGER_BUTTON_STYLE = solid_button_style(DANGER, "#FFFFFF")


def top_button_style(bg, fg, hover):
    return f"""
        QPushButton {{
            background-color: {bg};
            color: {fg};
            font-weight: bold;
            border-radius: 8px;
        }}
        QPushButton:hover {{
            background-color: {hover};
        }}
    """


def build_stylesheet(colors, theme):
    c = colors
    is_light = theme == "Light"
    hover_bg = "#000000" if is_light else "#ffffff"
    hover_fg = "#ffffff" if is_light else "#000000"
    handle = _rgba(c["text_muted"], 0.45)
    handle_hover = _rgba(c["text_muted"], 0.85)

    return f"""
        QMainWindow, QWidget#centralWidget {{
            background-color: {c['bg_dark']};
            color: {c['text_primary']};
            font-family: Consolas, monospace;
        }}
        QFrame#surface {{
            background-color: {c['bg_surface']};
            border: 1px solid {c['bg_panel']};
            border-radius: 8px;
        }}
        QFrame#panel {{
            background-color: {c['bg_panel']};
            border-radius: 6px;
        }}
        QLabel {{
            color: {c['text_primary']};
            background-color: transparent;
        }}
        QLabel#muted {{
            color: {c['text_muted']};
        }}
        QLabel#badge {{
            background-color: {c['bg_panel']};
            color: {c['text_primary']};
            border-radius: 4px;
            padding: 1px 6px;
            font-weight: bold;
        }}
        QPushButton {{
            background-color: {c['bg_panel']};
            color: {c['text_primary']};
            border: none;
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 11px;
        }}
        QPushButton:hover {{
            background-color: {hover_bg};
            color: {hover_fg};
        }}
        QPushButton:disabled {{
            color: {c['text_muted']};
        }}
        QComboBox {{
            background-color: {c['bg_dark']};
            color: {c['text_primary']};
            border: 1px solid {c['bg_panel']};
            border-radius: 4px;
            padding: 2px 6px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            width: 0px;
            height: 0px;
            margin-right: 6px;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {c['text_muted']};
        }}
        QComboBox QAbstractItemView {{
            background-color: {c['bg_dark']};
            color: {c['text_primary']};
            border: 1px solid {c['bg_panel']};
            selection-background-color: {c['accent']};
            selection-color: {contrast_text(c['accent'])};
            outline: 0;
            padding: 2px;
        }}
        QComboBox QAbstractItemView::item {{
            min-height: 22px;
            padding: 2px 6px;
        }}

        QSplitter::handle:vertical {{
            background-color: {c['bg_dark']};
            height: 5px;
        }}
        QSplitter::handle:vertical:hover {{
            background-color: #8AA090;
        }}

        QSlider::groove:horizontal {{
            height: 6px;
            background: {c['bg_dark']};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: #8AA090;
            border-radius: 3px;
        }}
        QSlider::add-page:horizontal {{
            background: {c['bg_dark']};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {c['accent']};
            width: 16px;
            height: 16px;
            margin-top: -5px;
            margin-bottom: -5px;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            background: #8B919E;
        }}

        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 2px 1px;
            border: none;
        }}
        QScrollBar::handle:vertical {{
            background: {handle};
            min-height: 28px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {handle_hover};
        }}
        QScrollBar::handle:vertical:pressed {{
            background: {c['accent']};
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 1px 2px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background: {handle};
            min-width: 28px;
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {handle_hover};
        }}
        QScrollBar::handle:horizontal:pressed {{
            background: {c['accent']};
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{
            width: 0px;
            height: 0px;
            background: transparent;
            border: none;
        }}
        QScrollBar::add-page, QScrollBar::sub-page {{
            background: transparent;
        }}

        QLineEdit {{
            background-color: {c['bg_dark']};
            color: {DANGER};
            border: 1px solid {DANGER};
            border-radius: 4px;
            font-weight: bold;
        }}
        QCheckBox {{
            color: {c['text_primary']};
            background-color: transparent;
        }}
        QTextEdit {{
            background-color: {c['bg_surface']};
            color: {c['text_primary']};
            border: none;
        }}
        QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
            border: none;
            background-color: transparent;
            background: transparent;
        }}
    """

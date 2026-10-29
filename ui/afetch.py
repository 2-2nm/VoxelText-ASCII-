import os

from PySide6.QtGui import QColor, QFont, QTextCharFormat

from core.utils import get_resource_path
from ui.sysinfo import current_user, get_sys_info

SEP_COLORS = {"Dark": "#5C6370", "Light": "#7A776F"}
SWATCHES = ["#767676", "#CCCCCC", "#3A96DD", "#881798", "#0037DA", "#C19C00", "#13A10E", "#C50F1F"]
SPEC_KEYS = [
    ("OS", "OS"), ("Kernel", "Kernel"), ("Uptime", "Uptime"), ("Date Time", "DateTime"),
    ("CPU", "CPU"), ("GPU", "GPU"), ("Memory", "Memory"), ("Disk", "Disk"), ("Terminal", "Terminal"),
]
LOGO_GAP = " " * 4
DOT = "●"  
RULE = "─" * 90


def _fmt(color, family="Consolas", size=9, bold=False, italic=False, bg=None):
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    fmt.setFont(QFont(family, size, QFont.Bold if bold else QFont.Normal, italic))
    if bg:
        fmt.setBackground(QColor(bg))
    return fmt


def load_ascii_logo():
    path = get_resource_path("ascii_terminal.txt")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return [line.rstrip("\r\n") for line in f.readlines()]
        except Exception:
            pass
    return []


def render_afetch(edit, colors, theme):
    info = get_sys_info()
    logo = load_ascii_logo()
    logo_width = max((len(line) for line in logo), default=0)

    fmt = {
        "cmd": _fmt(colors["cmd_prompt"], size=10, bold=True),
        "logo": _fmt(colors["cmd_prompt"]),
        "title": _fmt(colors["title_tag"], "Georgia", 16, italic=True),
        "sep": _fmt(SEP_COLORS.get(theme, SEP_COLORS["Dark"])),
        "key": _fmt(colors["key_tag"]),
        "val": _fmt(colors["val_tag"]),
        "note": _fmt(colors["note_tag"], italic=True),
    }

    edit.setReadOnly(False)
    edit.clear()
    put = edit.textCursor().insertText

    put(f" ┌──({current_user()}@vxl)-[~]\n └─$ afetch --system-diagnostics\n\n", fmt["cmd"])

    lines = [("title", info["title"]), ("sep", "─" * (len(info["title"]) + 2))]
    lines += [("spec", (name, info[key])) for name, key in SPEC_KEYS]
    palette_row = len(lines)

    for i in range(max(len(logo), len(lines) + 2)):
        if logo_width:
            put((logo[i] if i < len(logo) else "").ljust(logo_width) + LOGO_GAP, fmt["logo"])

        if i < palette_row:
            kind, content = lines[i]
            if kind == "spec":
                put(f"{content[0]:<10}: ", fmt["key"])
                put(f"{content[1]}\n", fmt["val"])
            else:
                put(content + "\n", fmt[kind])
        elif i == palette_row:
            put("Palette   : ", fmt["key"])
            for color in SWATCHES:
                put(DOT + " ", _fmt(color, size=11))
            put("\n", fmt["val"])
        else:
            put("\n", fmt["val"])

    put("\n" + RULE + "\n", fmt["sep"])
    put("           > Execute command to render local graphics into ASCII.            \n", fmt["note"])
    put(RULE + "\n", fmt["sep"])

    edit.setReadOnly(True)

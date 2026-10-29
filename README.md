# VoxelText

![Version](https://img.shields.io/badge/VERSION-4.0.0-FF6B6B?style=for-the-badge&labelColor=4a4f57)
![Python](https://img.shields.io/badge/PYTHON-3.8--3.13-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=4a4f57)
![GUI](https://img.shields.io/badge/GUI-PYSIDE6-41CD52?style=for-the-badge&logo=qt&logoColor=white&labelColor=4a4f57)
![Renderer](https://img.shields.io/badge/RENDERER-MODERNGL%20%2F%20OPENGL%203.3-5586A4?style=for-the-badge&logo=opengl&logoColor=white&labelColor=4a4f57)
![Platform](https://img.shields.io/badge/PLATFORM-WINDOWS%2010%20%2F%2011-0078D4?style=for-the-badge&logo=windows&logoColor=white&labelColor=4a4f57)
![License](https://img.shields.io/badge/LICENSE-MIT-9ACD32?style=for-the-badge&labelColor=4a4f57)

A desktop app that turns photos, videos, live games and **3D wireframe models** into ASCII art, rendered in real time on the GPU with OpenGL shaders (ModernGL).

<p align="center">
  <img width="800" height="500" alt="Voxel mode: a spinning 3D model drawn in ASCII" src="https://github.com/user-attachments/assets/2c9e56ea-c956-425b-8a12-49d314595bd6" />
</p>

<p align="center"><i>Voxel mode: a 3D model spinning in pure ASCII.</i></p>

## What's new in 4.0.0

- **Voxel mode (new):** a fourth tab that draws 3D wireframe models as ASCII, with depth shading
- **Built-in editor:** edit, draw and paint models right in the preview, with undo
- **VXL files:** save and load your models as `.vxl`
- **Free camera:** orbit, pan, zoom and fly around the model
- **Modular UI:** the interface is split into per-mode decks (`ui/decks/`), and a new `core/uidebug.py` can profile UI stalls
- **Build script renamed** to `build.bat`

## Voxel mode

Pick a preset (`torus`, `cube`, `pyramid`, `starship`, `blank`) or load a `.vxl` file, then let it spin or shape it yourself.

| Tool | What it does |
|---|---|
| **Edit** | Click a line to add a point, drag points to reshape, right-click a point to delete it |
| **Draw** | Click empty space to start a line and keep clicking to extend it. Right-click to finish |
| **Paint** | Click or drag over lines to color them. `Shift`+click colors the whole connected piece |

- **Camera:** `W`/`S` move in and out, `A`/`D` strafe, `Q`/`E` down and up (hold `Shift` for speed). Middle-drag orbits, `Shift`+middle-drag pans, scroll zooms toward the mouse.
- **Spin:** a slider sets the spin direction and speed. `Fit` resets the view and `Ctrl+Z` undoes.
- **Look:** the same colors, styles and glyph sets as the other modes.

## Game Stream

Pick any running game window and play it as live ASCII art. The picture is shown on a click-through overlay, so mouse and keyboard still reach the game. Use a **windowed** or **borderless** game, and **Pure ASCII** at about 150 to 250 columns for the most readable result.

## Features

- **Image, Video, Game and Voxel** modes, each with its own settings deck
- **Colors:** *Monochrome*, any custom color from the built-in color picker, or **Full Color** (*Blocky* or *Pure ASCII*)
- **Six glyph sets:** Standard, Fine, Classic, Blocks, Minimal, Digits
- **Video** with audio, pause, seek and mute, and **MP4 export** (H.264 + AAC via FFmpeg)
- **Image export** as high-resolution PNG (at least 2560 px wide) or `.txt`
- **Transparency modes** (White / Black) and adjustable width, with **Overdrive** for custom values
- **Command-line mode** for quick image to TXT conversion
- Dark / Light theme, fullscreen (`F11`), a console log panel and auto-saved settings

## Requirements

- Windows 10 / 11 and Python 3.8 - 3.13
- A GPU with OpenGL 3.3 support
- Packages: `PySide6`, `moderngl`, `numpy`, `opencv-python`, `Pillow`, `pygame-ce`, `imageio-ffmpeg` (or a system `ffmpeg` on your PATH)
- Optional: `windows-capture` (Game Stream), `psutil` (startup screen info), `pywinstyles` (dark title bar)

## Installation

```bash
git clone https://github.com/2-2nm/VoxelText-ASCII-.git
cd VoxelText-ASCII-
pip install PySide6 Pillow numpy opencv-python moderngl pygame-ce imageio-ffmpeg windows-capture psutil pywinstyles
python main.py
```

### Build a standalone .exe

Keep the folder structure as is. Optional assets such as `app-icon.ico` go in `assets/`. Then run:

```bat
build.bat
```

The result is saved to `dist\VoxelText.exe`.

## Usage

Open the **Image**, **Video**, **Game** or **Voxel** tab, load a file (or pick a window / model), choose a palette, style and glyph set, then adjust the width. Export with **Save as PNG** or **Save as MP4**, or **Save VXL** in Voxel mode. `F11` toggles fullscreen and `Esc` leaves it.

### Command line

```bash
python main.py --image photo.jpg --output photo_ascii.txt --width 120
```

| Option | Description |
|---|---|
| `--image`, `-i` | Input image file |
| `--output`, `-o` | Output TXT file (prints to the console if omitted) |
| `--width`, `-w` | Number of ASCII columns (default: 85) |
| `--version`, `-v` | Show the version (v4.0.0) |

Running `python main.py` with no arguments starts the GUI.

## Project structure

```text
VoxelText/
├── main.py              # Entry point (CLI, GPU hint, launches the GUI)
├── build.bat            # One-click Windows build (PyInstaller)
├── assets/              # Icons, logo and the demo GIF
├── core/                # Shaders, glyph sets, image pipeline, utils, UI stall profiler
├── ui/                  # PySide6 GUI: window, themes, preview, widgets, overlay
│   └── decks/           # One settings deck per mode (image, video, game, voxel)
├── video/               # GPU player, audio (FFmpeg + pygame), MP4 exporter
├── game/                # Window capture, GPU game player, window manager
└── voxel/               # 3D model, ASCII renderer, point picking, .vxl format
```

Settings are stored in `%APPDATA%\VoxelText\settings.json`.

## Known limitations

- Game Stream is Windows only. Exclusive fullscreen games may not be capturable, and anti-cheat games may block capture.
- Engage mode changes the game window while streaming. It is restored when you stop.
- Frames are read back from the GPU to the CPU, so GPU load is not 100%.
- MP4 export is not real time. Long videos at very high widths take a while.

## Credits

Built with Python, PySide6, OpenCV, ModernGL, pygame, FFmpeg and Pillow.

## License

MIT, see [LICENSE](LICENSE).

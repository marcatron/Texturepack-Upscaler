# Minecraft Texturepack Upscaler (32x / 48x / 64x)

A fast, intelligent standalone utility designed to upscale Minecraft resource packs with zero quality degradation, full support for OptiFine/Continuity Connected Textures (CTM glass/panes), texture animations, and clean alpha-channel transparency.

---

## ✨ Features

- **Smart Pixel-Art Scaling (Scale2x / EPX)**:
  - Smooths stepped pixel staircases and rounded corners cleanly without blurriness, smudging, or color degradation.
  - Supports **3x (48x48)** and **4x (64x64 HD)** upscaling modes as well.
- **CTM Glass & Transparency Awareness**:
  - Full support for transparent and semi-transparent glass panes (such as Jicklus CTM).
  - Proper edge-detection for fully transparent borders (`alpha == 0`) prevents ugly color fringing or halo artifacts.
- **Animation Frame Preservation**:
  - Automatically identifies vertical animation strips (via `.png.mcmeta` or aspect ratio) and upscales them frame-by-frame to prevent vertical frame bleeding.
- **Minecraft Compatibility Guardrails**:
  - Protects colormaps (`textures/colormap/` such as `grass.png`, `foliage.png`) at their strict 256x256 coordinate grid to ensure biome tinting remains accurate.
  - Automatically copies all non-image assets (`.json` models, `.properties`, `.mcmeta`, `.txt`, `.ogg` sounds, language files) untouched.
  - Automatically updates `pack.mcmeta` with the target resolution label.
- **Folder & ZIP Support**:
  - Accepts standard resource pack folders as well as `.zip` archives for both input and output.
- **Modern Graphical User Interface (PyQt5)**:
  - Drag & Drop packs directly into the application window.
  - Real-time progress bar, currently processed file indicator, and detailed log viewer.
  - Auto-detects logical CPU threads for maximum multicore throughput.
- **Command-Line Interface (CLI)**:
  - Can be fully automated in scripts or terminal sessions.
- **Standalone Binary**:
  - Can run via Python or directly as a compiled Windows executable without needing a Python environment.

---

## 🚀 Quick Start (GUI)

Simply double-click:
```text
run_gui.bat
```
*(Or use `start_standalone_exe.bat` to launch the compiled standalone executable).*

Alternatively, run from a terminal:
```bash
python main.py
```

### Steps:
1. Drag & drop your resource pack (`.zip` or folder) into the window (or click **Ordner...** / **ZIP Datei...**).
2. The destination path is automatically populated with the resolution suffix (e.g., `_32x`).
3. Select your desired algorithm (default: **Scale2x / EPX** for 32x32).
4. Click **Upscaling starten** (Start Upscaling).
5. When finished, click **Zielordner öffnen** (Open Output Folder) to inspect your new pack.

---

## 💻 Command-Line Interface (CLI)

```bash
# Standard 32x upscale using Scale2x (EPX)
python main.py -i "C:\Path\To\MyPack" -o "C:\Path\To\MyPack_32x"

# Direct ZIP to ZIP upscale
python main.py -i "MyPack.zip" -o "MyPack_32x.zip"

# 48x48 upscale (Scale3x) or 64x64 HD upscale (Scale4x)
python main.py -i "MyPack" --algorithm scale4x

# Display CLI help and arguments
python main.py --help
```

### CLI Arguments

| Flag | Parameter | Description |
|---|---|---|
| `-i` | `--input` | Path to the source resource pack (`.zip` or folder) |
| `-o` | `--output` | Path to the target output (`.zip` or folder) |
| `-a` | `--algorithm` | Algorithm: `scale2x`, `scale3x`, `scale4x`, `nearest`, `lanczos`, `bicubic` |
| `-s` | `--scale` | Scaling factor multiplier (`2`, `3`, `4`) |
| `-w` | `--workers` | Number of worker threads (default: auto-detected CPU threads) |

---

## ⚙️ Algorithms

- **Scale2x / EPX** *(Recommended)*: Smooths pixel corners and diagonal staircases into clean edges while keeping pixel art crisp and true to original palette.
- **Scale3x / AdvMAME3x**: 3x upscale for 48x48 resolution.
- **Scale4x**: Two consecutive Scale2x passes for 64x64 HD packs.
- **Nearest Neighbor**: Exact 1:1 pixel duplication (preserves identical blocky pixels).
- **Lanczos**: Filtered anti-aliasing with subtle sharpening.
- **Bicubic**: Standard smooth resampling.

---

## 🛠️ Requirements & Installation

Python 3.10+ is supported. Install dependencies with:
```bash
pip install -r requirements.txt
```

Required packages:
- `Pillow >= 10.0.0`
- `numpy >= 1.24.0`
- `PyQt5 >= 5.15.0`

---

## 📦 Building Standalone Windows Executable

To compile into a standalone `.exe`:
```text
build_exe.bat
```
The compiled application will be generated in `dist\TexturepackUpscaler\TexturepackUpscaler.exe`.

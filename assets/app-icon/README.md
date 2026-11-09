# OpenPDF app icon

<img src="openpdf-small.svg" alt="OpenPDF app icon: an engraved lion's head on red" width="128">

**Creature:** a lion, in a frontal head-and-shoulders portrait, mane running off the bottom of the tile.

**Style:** an engraving (woodcut-weight line work) portrait in the Crafting Apps "owl template" framing:
a full-bleed colour field, no frame or roundel, the animal looking at the viewer and filling the tile.

**Palette:** exactly three colours.

| Colour | Hex | Used for |
|---|---|---|
| Ink | `#0b0b0c` | line work and the figure's contour |
| Paper | `#efe9dc` | the figure (the lion's silhouette) |
| OpenPDF red (app colour) | `#b70228` | the full-bleed field |

**Tile:** `viewBox="0 0 512 512"`, a rounded square with `rx=112` that clips everything. Windows and Linux
icons use the full-bleed tile. macOS icons put it on Apple's grid (an 824 px body centred on a transparent
1024 px canvas).

**Provenance:** the PdfCraft project's original drawing, made in ArtCraft (2880 px, keyed to the palette), then
vectorised (potrace; no filtering or warping).
Licence: [LICENSE.txt](LICENSE.txt) (`MIT OR Apache-2.0`, like the repo).

## Files

| File | What it is |
|---|---|
| `openpdf.svg` | the master vector (traced at 2048 px); every PNG, `.ico` and `.icns` is rendered from it |
| `openpdf-small.svg` | a lighter vector (traced at 1024 px) for places where size matters, such as this README |
| `openpdf-1024.png` | 1024 px on Apple's grid; also the runtime Dock icon on macOS |
| `openpdf.icns` | macOS icon (16–1024 px) |
| `openpdf.ico` | Windows icon (16–256 px), embedded in `openpdf.exe` by `apps/openpdf/build.rs` |
| `openpdf-document.svg` | Windows PDF file icon master: a Lucide document outline, red badge and outlined PDF lettering; no font dependency |
| `openpdf-document.ico` | Windows PDF file icon (16–256 px), embedded as resource 2 in `openpdf.exe` |
| `hicolor/<n>x<n>/apps/io.github.openscientificsoftware.openpdf.png` | Linux hicolor theme, 16–512 px; the 256 px one is the runtime icon on Windows and Linux |
| `hicolor/scalable/apps/io.github.openscientificsoftware.openpdf.svg` | Linux scalable icon (copy of the master) |

Where it shows: `apps/openpdf/src/main.rs` sets the window icon (Dock, taskbar, Alt-Tab, launcher) and the
Wayland app id `io.github.openscientificsoftware.openpdf`; `packaging/linux/io.github.openscientificsoftware.openpdf.desktop` names the
hicolor icon.

Windows PDF files use resource 2 (`"openpdf.exe",-2`) when OpenPDF is chosen as the default
reader; the app keeps resource 1. The document outline is adapted from Lucide `file-text`
1.49.0 (ISC); its badge and outlined lettering are original (`MIT OR Apache-2.0`), covered by
[LICENSE-document.txt](LICENSE-document.txt). Both icons are embedded, requiring no runtime
sidecar. This provides a file type icon; first-page thumbnails still need a thumbnail provider.

## Regenerate

```sh
packaging/icons.sh        # needs resvg and python3; iconutil (macOS) for the .icns
cargo xtask assets        # then update the sha256 values in ATTRIBUTION.toml and run with --write
```

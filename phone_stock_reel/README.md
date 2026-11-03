# New Phone Stock Reel

A 22-second vertical Instagram Reel (9:16, 1080×1920, 30 fps) for a mobile phone store's new stock drop.

| File | What it is |
|---|---|
| `phone_stock_reel.mp4` | Final reel: colour-graded footage, beat-synced cuts and zooms, animated captions, original music |
| `music.py` | Builds the original 120 BPM electronic/hip-hop track (`python3 music.py music.wav`) |
| `render.py` | Renders the video and muxes the music (`python3 render.py out.mp4 music.wav`) |

The source clips (`IMG_7132.MP4`, `IMG_7133.MOV`, `IMG_7134.MOV`) are not in the repo. To re-render, put them in `source/` or point `SRC_DIR` at their folder. Needs Python 3, NumPy, SciPy, OpenCV, Pillow, ffmpeg, and the Inter and Noto Color Emoji fonts.

Caption sequence: WAIT FOR IT... 👀 → NEW STOCK ALERT 🚨 → FRESH ARRIVALS / JUST LANDED → MULTIPLE MODELS. PREMIUM PICKS. → WHICH ONE IS YOUR FAVOURITE? → DM NOW TO RESERVE YOURS

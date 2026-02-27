# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies (using uv):**
```bash
uv sync
```

**Run (must be executed from the repository root so `index.html` and `app.js` can be copied):**
```bash
python main.py --target /path/to/videos
python main.py --target /path/to/videos --recursive
```

## Architecture

This is a video snapshot generator with a static HTML viewer.

**Python backend (`main.py`, `snapshot.py`):**
- `Snapshot` class wraps a single `.mp4` file. It computes a SHA256 hash of the first 10MB (`CHUNK_SIZE`) to create a unique output directory at `.snapshots/{sha256}/` adjacent to the video file.
- `make_snapshot()` in `snapshot.py` uses OpenCV to extract 16 evenly-spaced frames, resized to 250px wide, saved as `1.jpg`–`16.jpg`.
- Processing is parallelized via `ProcessPoolExecutor` (max 4 workers).
- After all videos are processed, `dump_jsonfile()` writes `snapshots.json` and `snapshots.js` (`const videos = [...]`) into the `--target` directory, then copies `index.html` and `app.js` there for viewing.
- `get_target_list2()` handles optional recursive `.mp4` discovery across subdirectories.

**Frontend viewer (`index.html`, `app.js`):**
- Vanilla JS, no build step. Loaded via the copied files in the target directory.
- Reads video metadata from the co-located `snapshots.js`.
- `ListItem` renders one video card; clicking the thumbnail cycles through its snapshots.
- Video links use `potplayer://` protocol for PotPlayer integration alongside a standard browser link.

**Key data shape** (`Snapshot.to_dict()`):
```json
{
  "name": "video-stem",
  "target": "posix/path/to/file.mp4",
  "snapshots": ["path/to/1.jpg", ...],
  "sha256": "abc123...",
  "dirname": "parent-folder-name"
}
```

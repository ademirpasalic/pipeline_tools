# pipeline_tools

A collection of standalone VFX/animation pipeline tools for production studios.
Eleven Python/PySide6 desktop GUIs and one TypeScript/Express web server.

## Tools

| Tool | Description |
|------|-------------|
| `asset_validator` | Validate naming conventions, folder structure, and file metadata against configurable rulesets |
| `batch_renamer` | Rename and organize files with regex patterns, presets, find-and-replace, and numbering |
| `dcc_launcher` | Launch Maya, Blender, Houdini, and Nuke with the correct project environment variables |
| `file_collector` | Gather files from multiple locations, package them for delivery, and generate MD5 manifests |
| `file_ingestor` | Classify, rename, and copy incoming files into a structured pipeline folder hierarchy |
| `frames_video` | Convert image sequences (EXR, PNG, JPG) to video and extract frames from video |
| `media_converter` | Batch convert between image and video formats using Pillow and ffmpeg |
| `pipeline_config` | Manage per-project YAML/JSON pipeline configs with path templates and a visual editor |
| `production_tracker` | Lightweight shot/asset status dashboard backed by a local JSON database |
| `scene_publisher` | Version-stamp and publish scene files with JSON sidecar metadata and publish history |
| `video_concat` | Join multiple video clips together with optional audio strip and reorder support |
| `webhook_monitor` | Real-time web dashboard for monitoring pipeline events via Server-Sent Events |

## Requirements

**Python tools**
```bash
pip install PySide6 Pillow PyYAML
```
- `ffmpeg` in PATH — required by `frames_video`, `media_converter`, `video_concat`

**webhook_monitor**
```bash
cd webhook_monitor
npm install
```

## Running the tools

Each Python tool is a self-contained script:

```bash
python asset_validator/asset_validator.py
python batch_renamer/batch_renamer.py
python dcc_launcher/dcc_launcher.py
python file_collector/file_collector.py
python file_ingestor/file_ingestor.py
python frames_video/frames_video.py
python media_converter/media_converter.py
python pipeline_config/pipeline_config.py
python production_tracker/production_tracker.py
python scene_publisher/scene_publisher.py
python video_concat/video_concat.py
```

**webhook_monitor**
```bash
cd webhook_monitor
npm run build   # compile TypeScript
npm start       # serve on http://localhost:3000

# Send a test event
curl -X POST http://localhost:3000/api/webhook \
  -H "Content-Type: application/json" \
  -d '{"source": "shotgrid", "event": "publish.complete", "data": {"asset": "hero_rig_v012"}}'
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest                                        # all tests
pytest tests/test_asset_validator.py -v       # single tool
```

Tests run headless via `QT_QPA_PLATFORM=offscreen` (set automatically in `conftest.py`).

## Architecture

Every Python tool follows the same pattern:

1. **Engine class** — pure logic, no Qt dependency, fully unit-testable
2. **MainWindow** — PySide6 GUI wrapping the engine
3. **main()** — creates `QApplication` and shows the window

The engine class is always safe to import and test without a display.

## Author

Ademir Pasalic

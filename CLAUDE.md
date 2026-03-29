# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A collection of standalone VFX/animation pipeline tools for production studios. Eleven tools are Python/PySide6 desktop GUIs; one (`webhook_monitor`) is a TypeScript/Express web server.

## Versioning & PR Policy

Each tool is versioned independently using **semver** (`MAJOR.MINOR.PATCH`). All tools start at `0.1.0`.

| Bump | When | Who merges |
|------|------|------------|
| `MAJOR` | Breaking changes, full architectural redesigns | User reviews & merges PR |
| `MINOR` | New features, UX improvements, notable enhancements | User reviews & merges PR |
| `PATCH` | Bug fixes, small improvements, refactors with no visible change | Agents review & merge autonomously |

Always open a branch named `<tool>/<version>` (e.g. `scene_publisher/0.2.0`) and label the PR with the bump type.

## Testing

```bash
pip install -r requirements-dev.txt
pytest                    # run all tests
pytest tests/test_asset_validator.py          # single tool
pytest tests/test_production_tracker.py -v   # verbose
```

Qt GUI tests run headless via `QT_QPA_PLATFORM=offscreen` (set automatically in `conftest.py`). Engine classes have no Qt dependency and can always be tested directly.

## Running the Tools

Each Python tool is a self-contained script — run directly:

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

### webhook_monitor (Node.js/TypeScript)

```bash
cd webhook_monitor
npm install        # first time only
npm run build      # compile TypeScript → dist/
npm start          # run compiled server (port 3000)
npm run dev        # run with ts-node (no compile step)
npm run demo       # POST 18 sample events to localhost:3000
```

## Dependencies

**Python tools** — install as needed:
- `PySide6` — all GUIs (falls back to `PyQt5` in some tools)
- `Pillow` — `media_converter`, `scene_publisher`
- `PyYAML` — `pipeline_config` (optional; falls back to JSON)
- `FFmpeg` (system binary) — `frames_video`, `media_converter`, `video_concat`

**webhook_monitor** — managed by `package.json` (`express`, `typescript`, `ts-node`)

## Architecture

### Python GUI Pattern

Every Python tool follows the same structure:
1. A data/engine class with pure logic (no Qt)
2. A `MainWindow(QMainWindow)` that wraps the engine
3. A `main()` entry point that creates `QApplication` and shows the window

The engine class is always safe to import and unit-test without a display.

### Data Flow

```
Incoming files
  → file_ingestor   (classifies by extension into scenes/textures/cache/video/audio/docs)
  → batch_renamer   (normalize names before ingestion)

Artist work (inside DCCs)
  → dcc_launcher    (spawns Maya/Blender/Houdini/Nuke with project env vars from launcher_config.json)

Output/delivery
  → asset_validator (validates naming conventions + folder structure)
  → scene_publisher (version-stamps scenes → published/<asset>/<v001>/ + JSON sidecar)
  → frames_video    (image sequences ↔ video)
  → media_converter (batch format conversion)
  → video_concat    (join multiple clips)
  → file_collector  (gather files, compute MD5s, write delivery manifest)

Tracking
  → production_tracker (shot/asset status dashboard backed by tracker_db.json)
  → pipeline_config    (manage per-project YAML/JSON config with path templates)

Monitoring
  → webhook_monitor (Express SSE server; any tool can POST JSON events to /api/webhook)
```

### Key Config Files

| File | Used by |
|------|---------|
| `launcher_config.json` | `dcc_launcher` — project env vars and DCC executable paths |
| `tracker_db.json` | `production_tracker` — persistent shot/asset records |

### webhook_monitor API

- `POST /api/webhook` — ingest an event `{ source, event, severity?, data? }`
- `GET /api/events?source=&severity=&search=` — query buffered events (last 1000)
- `GET /api/stats` — aggregate counts by severity/source + events/min rate
- `GET /api/stream` — Server-Sent Events for real-time dashboard

Severity is auto-inferred from event name if not supplied (`publish.complete` → `success`, `*.error` → `error`, etc.).

### Asset Validation Rules

`asset_validator` enforces:
- Filename regex: `^[a-z][a-z0-9]*(_[a-z0-9]+)*\.[a-z0-9]+$` (max 80 chars)
- Forbidden characters: `#`, space, `(`, `)`, `&`, `!`, `@`
- Required folders: `assets`, `textures`, `scenes`, `cache`, `output`
- Max file size: 500 MB; max file age: 365 days

### Scene Publisher Version Scheme

Publishes to `published/<asset_name>/v001/`, auto-incrementing. Each publish writes a JSON metadata sidecar alongside the file (artist, comment, source path, timestamp, file size).

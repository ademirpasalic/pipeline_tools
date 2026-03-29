"""
Root pytest configuration.
Sets up headless Qt and adds each tool directory to sys.path.
"""
import os
import sys

# Run Qt without a display (headless CI / test environments)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ROOT = os.path.dirname(__file__)
# shared/ package must be importable from tool scripts
sys.path.insert(0, _ROOT)

for _tool in [
    "asset_validator", "batch_renamer", "dcc_launcher", "file_collector",
    "file_ingestor", "frames_video", "media_converter", "pipeline_config",
    "production_tracker", "scene_publisher", "video_concat",
]:
    sys.path.insert(0, os.path.join(_ROOT, _tool))

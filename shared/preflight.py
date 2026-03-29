"""
Startup dependency checks for pipeline tools.

Usage:
    from shared.preflight import require_ffmpeg, require_pillow, check_writable

    # In tool's main():
    require_ffmpeg()   # shows dialog and exits if ffmpeg not found
    require_pillow()   # shows dialog and exits if Pillow not installed
"""
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PySide6 import QtWidgets
except ImportError:
    from PyQt5 import QtWidgets


# ── Internal helpers ─────────────────────────────────────────────────────────

def _ffmpeg_version() -> str | None:
    """Return ffmpeg version string, or None if not found."""
    exe = shutil.which("ffmpeg")
    if not exe:
        return None
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        first_line = result.stdout.splitlines()[0] if result.stdout else ""
        return first_line or "unknown version"
    except Exception:
        return None


def _pillow_version() -> str | None:
    """Return Pillow version string, or None if not installed."""
    try:
        import PIL
        return getattr(PIL, "__version__", "installed")
    except ImportError:
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def check_ffmpeg() -> tuple[bool, str]:
    """Check whether ffmpeg is available on PATH.

    Returns:
        (available, message) — message is the version string or an error hint.
    """
    version = _ffmpeg_version()
    if version:
        return True, version
    return False, "ffmpeg not found on PATH. Install from https://ffmpeg.org/download.html"


def check_pillow() -> tuple[bool, str]:
    """Check whether Pillow is installed.

    Returns:
        (available, message)
    """
    version = _pillow_version()
    if version:
        return True, f"Pillow {version}"
    return False, "Pillow not installed. Run: pip install Pillow"


def check_writable(path: str | Path) -> tuple[bool, str]:
    """Check whether path is writable (creating it if necessary).

    Returns:
        (writable, message)
    """
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".write_test"
        test.touch()
        test.unlink()
        return True, str(p)
    except PermissionError:
        return False, f"No write permission: {p}"
    except Exception as exc:
        return False, f"Cannot access {p}: {exc}"


def require_ffmpeg(parent: "QtWidgets.QWidget | None" = None) -> None:
    """Show a blocking error dialog and exit if ffmpeg is not available."""
    ok, msg = check_ffmpeg()
    if not ok:
        _fatal(parent, "Missing Dependency: ffmpeg", msg)


def require_pillow(parent: "QtWidgets.QWidget | None" = None) -> None:
    """Show a blocking error dialog and exit if Pillow is not installed."""
    ok, msg = check_pillow()
    if not ok:
        _fatal(parent, "Missing Dependency: Pillow", msg)


def _fatal(parent, title: str, message: str) -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    QtWidgets.QMessageBox.critical(parent, title, message)
    sys.exit(1)

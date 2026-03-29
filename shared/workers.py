"""
Shared QThread worker base classes for pipeline tools.

Usage:
    from shared.workers import BaseWorker

    class MyWorker(BaseWorker):
        def work(self):
            for i, item in enumerate(self.items):
                if self.is_cancelled:
                    break
                # ... do work ...
                self.emit_progress(i * 100 // len(self.items), item)
            return result

    worker = MyWorker()
    worker.signals.progress.connect(on_progress)
    worker.signals.finished.connect(on_done)
    worker.signals.error.connect(on_error)
    worker.start()
    # worker.cancel() to abort
"""
try:
    from PySide6 import QtCore
    _Signal = QtCore.Signal
except ImportError:
    from PyQt5 import QtCore
    _Signal = QtCore.pyqtSignal


class WorkerSignals(QtCore.QObject):
    """Signals emitted by BaseWorker during its lifecycle."""

    started = _Signal()
    progress = _Signal(int, str)   # percent (0-100), status message
    finished = _Signal(object)     # result returned by work()
    error = _Signal(str)           # human-readable error message


class BaseWorker(QtCore.QThread):
    """Thread base class for pipeline tool background operations.

    Subclass and override :meth:`work`. Do not override :meth:`run`.
    Check :attr:`is_cancelled` inside work() loops to support cancellation.

    Signals are on :attr:`signals` (a :class:`WorkerSignals` instance).
    """

    def __init__(self) -> None:
        super().__init__()
        self.signals = WorkerSignals()
        self._cancelled = False

    # ── Public API ──────────────────────────────────────────────────────────

    def cancel(self) -> None:
        """Request cancellation. work() must check is_cancelled to honour it."""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def emit_progress(self, percent: int, message: str = "") -> None:
        """Convenience wrapper — call from inside work()."""
        self.signals.progress.emit(max(0, min(100, percent)), message)

    # ── QThread override ────────────────────────────────────────────────────

    def run(self) -> None:
        self.signals.started.emit()
        try:
            result = self.work()
            self.signals.finished.emit(result)
        except Exception as exc:
            self.signals.error.emit(str(exc))

    # ── Subclass interface ──────────────────────────────────────────────────

    def work(self):
        """Override in subclass. Return a result that will be passed to finished."""
        raise NotImplementedError

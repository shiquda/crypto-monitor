import logging

from PyQt6.QtCore import QObject, QThread

logger = logging.getLogger(__name__)


class WorkerController(QObject):
    """
    Centralized controller for managing worker thread lifecycles.
    Prevents premature garbage collection and ensures proper cleanup.
    """

    _instance = None

    def __init__(self):
        super().__init__()
        self._active_workers: list[QThread] = []
        self._dying_workers: list[QThread] = []

    @classmethod
    def get_instance(cls) -> "WorkerController":
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def register_worker(self, worker: QThread):
        """Register a new active worker."""
        if worker not in self._active_workers:
            self._active_workers.append(worker)
            # Connect finished signal to cleanup
            # Use a lambda that captures the worker weakly or handle carefully
            # Here we just rely on _on_worker_finished looking it up
            worker.finished.connect(lambda: self._on_worker_finished(worker))
            logger.debug(f"Worker registered: {worker}")

    def stop_worker(self, worker: QThread | None):
        """
        Safely stop and cleanup a worker.
        Moves it to dying list to survive until finished.
        """
        if not worker:
            return

        # Remove from active list
        if worker in self._active_workers:
            self._active_workers.remove(worker)

        # Detach from parent so it doesn't get destroyed with parent
        worker.setParent(None)

        if worker.isRunning():
            logger.debug(f"Stopping worker (async): {worker}")
            self._dying_workers.append(worker)

            # Call stop if available (BaseWebSocketWorker), else terminate/quit?
            # Our workers have stop() method.
            if hasattr(worker, "stop"):
                worker.stop()
            else:
                worker.quit()
                worker.wait()
        else:
            logger.debug(f"Worker already stopped, deleting: {worker}")
            worker.deleteLater()

    def _on_worker_finished(self, worker: QThread):
        """Handle worker finish event."""
        logger.debug(f"Worker finished: {worker}")

        if worker in self._active_workers:
            self._active_workers.remove(worker)

        if worker in self._dying_workers:
            self._dying_workers.remove(worker)

        worker.deleteLater()

    def cleanup_all(self):
        """Force cleanup of all workers (e.g. on app exit)."""
        logger.info("Cleaning up all workers...")
        all_workers = self._active_workers + self._dying_workers
        for worker in all_workers:
            if worker.isRunning():
                if hasattr(worker, "stop"):
                    worker.stop()
                else:
                    worker.quit()
            worker.wait(1000)  # Wait max 1s
            worker.deleteLater()

        self._active_workers.clear()
        self._dying_workers.clear()

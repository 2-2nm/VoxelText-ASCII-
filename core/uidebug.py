import os
import time

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voxeltext_debug.log")


def make_app_class(threshold_ms):
    class TimedApplication(QApplication):
        def notify(self, receiver, event):
            t0 = time.perf_counter()
            try:
                return super().notify(receiver, event)
            finally:
                ms = (time.perf_counter() - t0) * 1000.0
                if ms >= threshold_ms:
                    kind = event.type()
                    name = getattr(kind, "name", str(kind))
                    line = f"[stall {ms:6.1f} ms] {name:<22} -> {type(receiver).__name__}#{receiver.objectName()}"
                    print(line, flush=True)
                    try:
                        with open(LOG_PATH, "a", encoding="utf-8") as f:
                            f.write(line + "\n")
                    except OSError:
                        pass

    return TimedApplication

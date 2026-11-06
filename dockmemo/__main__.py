"""入口：python -m dockmemo"""
import sys

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __app_name__
from .app import DockMemoWindow
from .styles import APP_DIR


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    # 单实例保护：避免两个实例同时轮询、互相覆盖 notes.json
    APP_DIR.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(APP_DIR / "dockmemo.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, __app_name__, "DockMemo 已在运行，请勿重复启动。")
        sys.exit(0)

    window = DockMemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

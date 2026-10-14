"""入口：python -m dockmemo"""
import sys
from PySide6.QtWidgets import QApplication
from .app import DockMemoWindow


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    window = DockMemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

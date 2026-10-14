"""自定义控件"""
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from .styles import PRIMARY_TEXT, SECONDARY_TEXT, MUTED_TEXT


class NoteListItem(QWidget):
    """笔记列表中的每一项"""

    def __init__(self, note, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        title = note.get("title", "无标题")
        updated = note.get("updated_at", "")
        try:
            dt = datetime.fromisoformat(updated)
            time_str = dt.strftime("%m-%d %H:%M")
        except Exception:
            time_str = ""

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-weight: 600; font-size: 13px; color: {PRIMARY_TEXT};"
        )
        title_label.setWordWrap(True)

        preview = note.get("content", "").strip().split("\n")[0][:45]
        preview_label = QLabel(preview or "（空笔记）")
        preview_label.setStyleSheet(
            f"font-size: 11px; color: {SECONDARY_TEXT};"
        )
        preview_label.setWordWrap(True)

        time_label = QLabel(time_str)
        time_label.setStyleSheet(f"font-size: 10px; color: {MUTED_TEXT};")

        layout.addWidget(title_label)
        layout.addWidget(preview_label)
        layout.addWidget(time_label)

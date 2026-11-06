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

        self.title_label = QLabel()
        self.title_label.setStyleSheet(
            f"font-weight: 600; font-size: 13px; color: {PRIMARY_TEXT};"
        )
        self.title_label.setWordWrap(True)

        self.preview_label = QLabel()
        self.preview_label.setStyleSheet(
            f"font-size: 11px; color: {SECONDARY_TEXT};"
        )
        self.preview_label.setWordWrap(True)

        self.time_label = QLabel()
        self.time_label.setStyleSheet(f"font-size: 10px; color: {MUTED_TEXT};")

        layout.addWidget(self.title_label)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.time_label)

        self.set_note(note)

    def set_note(self, note):
        """（就地）刷新显示内容，用于自动保存时不重建列表项"""
        self.title_label.setText(note.get("title") or "无标题")
        preview = note.get("content", "").strip().split("\n")[0][:45]
        self.preview_label.setText(preview or "（空笔记）")
        self.time_label.setText(self._format_time(note.get("updated_at", "")))

    @staticmethod
    def _format_time(iso):
        try:
            return datetime.fromisoformat(iso).strftime("%m-%d %H:%M")
        except Exception:
            return ""

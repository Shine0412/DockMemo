"""主窗口"""
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction, QKeySequence, QCursor, QIcon, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QPushButton,
    QSystemTrayIcon, QMenu, QLabel, QFrame, QSplitter, QStyle,
    QInputDialog, QMessageBox
)

from . import __app_name__
from .styles import (
    EXPANDED_WIDTH, COLLAPSED_WIDTH, SCREEN_EDGE_MARGIN, HIDE_DELAY_MS,
    BG_COLOR, CARD_COLOR, BORDER_COLOR, PRIMARY_TEXT, SECONDARY_TEXT,
    MUTED_TEXT, ACCENT, ACCENT_HOVER, SELECTED_BG, DANGER, DANGER_HOVER,
    SUCCESS, HOVER_BG,
)
from .storage import load_notes, save_notes, load_config, save_config, create_note
from .widgets import NoteListItem
from .autostart import is_enabled as autostart_enabled, enable as autostart_enable, disable as autostart_disable, is_supported as autostart_supported


class DockMemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.notes = load_notes()
        self.current_note_id = None
        self.is_expanded = False
        self._expand_time = 0  # 展开时间戳，用于宽限期

        self.edit_timer = QTimer()
        self.edit_timer.setSingleShot(True)
        self.edit_timer.timeout.connect(self.save_current_note)

        self._load_icon()
        self.init_ui()
        self.init_tray()
        self.init_detect_timer()
        self.align_to_edge()
        self.collapse()

    # ---------- 图标 ----------
    def _load_icon(self):
        if hasattr(sys, "_MEIPASS"):
            base = Path(sys._MEIPASS)
        else:
            base = Path(__file__).parent.parent
        icon_path = base / "assets" / "icon.ico"
        if icon_path.exists():
            self.app_icon = QIcon(str(icon_path))
        else:
            self.app_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)

    # ---------- UI ----------
    def init_ui(self):
        self.setWindowTitle(__app_name__)
        self.setWindowIcon(self.app_icon)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        central = QWidget()
        central.setStyleSheet(f"background-color: {BG_COLOR};")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # === 顶部栏 ===
        header = QFrame()
        header.setStyleSheet(f"background-color: {CARD_COLOR}; border-bottom: 1px solid {BORDER_COLOR};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 10)
        header_layout.setSpacing(8)

        # 标题行：收起按钮 + 应用名 + 新建/删除
        title_row = QHBoxLayout()

        collapse_btn = QPushButton("‹")
        collapse_btn.setCursor(Qt.PointingHandCursor)
        collapse_btn.setFixedWidth(28)
        collapse_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 2px 0;
                background-color: transparent;
                color: {SECONDARY_TEXT};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {HOVER_BG};
                color: {PRIMARY_TEXT};
            }}
        """)
        collapse_btn.clicked.connect(self.collapse)
        title_row.addWidget(collapse_btn)
        title_row.addSpacing(6)

        app_label = QLabel(__app_name__)
        app_label.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {PRIMARY_TEXT}; letter-spacing: 0.5px;"
        )
        title_row.addWidget(app_label)
        title_row.addStretch()

        # 保存状态指示
        self.save_indicator = QLabel("已保存")
        self.save_indicator.setStyleSheet(f"font-size: 10px; color: {SUCCESS};")
        title_row.addWidget(self.save_indicator)
        title_row.addSpacing(8)

        delete_btn = QPushButton("删除")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 5px 12px;
                background-color: transparent;
                color: {DANGER};
                border: 1px solid {DANGER};
                border-radius: 6px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {DANGER}; color: white; }}
        """)
        delete_btn.clicked.connect(self.delete_current_note)
        title_row.addWidget(delete_btn)

        new_btn = QPushButton("+ 新建")
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setStyleSheet(f"""
            QPushButton {{
                padding: 5px 14px;
                background-color: {ACCENT};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {ACCENT_HOVER}; }}
        """)
        new_btn.clicked.connect(self.create_note)
        title_row.addWidget(new_btn)
        header_layout.addLayout(title_row)

        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索笔记...")
        self.search_box.setStyleSheet(f"""
            QLineEdit {{
                padding: 7px 12px;
                background-color: {BG_COLOR};
                border: 1px solid {BORDER_COLOR};
                border-radius: 6px;
                font-size: 12px;
                color: {PRIMARY_TEXT};
            }}
            QLineEdit:focus {{
                border-color: {ACCENT};
                background-color: {CARD_COLOR};
            }}
        """)
        self.search_box.textChanged.connect(self.refresh_list)
        header_layout.addWidget(self.search_box)

        # === 笔记列表 ===
        list_container = QFrame()
        list_container.setStyleSheet(f"background-color: {CARD_COLOR};")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        self.note_list = QListWidget()
        self.note_list.setStyleSheet(f"""
            QListWidget {{
                border: none;
                background-color: {CARD_COLOR};
                outline: none;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {BORDER_COLOR};
                border-left: 3px solid transparent;
            }}
            QListWidget::item:selected {{
                background-color: {SELECTED_BG};
                border-left: 3px solid {ACCENT};
            }}
            QListWidget::item:hover {{
                background-color: {HOVER_BG};
            }}
        """)
        self.note_list.itemClicked.connect(self.on_note_selected)
        # 右键菜单
        self.note_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.note_list.customContextMenuRequested.connect(self.show_list_context_menu)
        list_layout.addWidget(self.note_list)

        # === 编辑区 ===
        edit_container = QFrame()
        edit_container.setStyleSheet(f"background-color: {CARD_COLOR}; border-top: 1px solid {BORDER_COLOR};")
        edit_layout = QVBoxLayout(edit_container)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(0)

        # 标题输入框（可编辑文件名/笔记名）
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("笔记标题...")
        self.title_edit.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                border-bottom: 1px solid {BORDER_COLOR};
                background-color: {CARD_COLOR};
                padding: 10px 14px 8px 14px;
                font-size: 14px;
                font-weight: 600;
                color: {PRIMARY_TEXT};
            }}
        """)
        self.title_edit.textChanged.connect(self.on_title_changed)
        edit_layout.addWidget(self.title_edit)

        # 正文编辑区
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("在这里记录...\n\n内容会自动保存。")
        self.editor.setStyleSheet(f"""
            QTextEdit {{
                border: none;
                background-color: {CARD_COLOR};
                padding: 10px 14px;
                font-size: 13px;
                line-height: 1.6;
                color: {PRIMARY_TEXT};
            }}
        """)
        self.editor.textChanged.connect(self.on_text_changed)
        edit_layout.addWidget(self.editor)

        # === 底部状态栏 ===
        status_bar = QFrame()
        status_bar.setStyleSheet(f"background-color: {CARD_COLOR}; border-top: 1px solid {BORDER_COLOR};")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(14, 6, 14, 6)
        self.status_label = QLabel("0 条笔记")
        self.status_label.setStyleSheet(f"font-size: 10px; color: {MUTED_TEXT};")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.word_count_label = QLabel("0 字")
        self.word_count_label.setStyleSheet(f"font-size: 10px; color: {MUTED_TEXT};")
        status_layout.addWidget(self.word_count_label)

        # === 组装 ===
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(1)
        splitter.addWidget(list_container)
        splitter.addWidget(edit_container)
        splitter.setSizes([240, 280])
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {BORDER_COLOR}; }}")

        root.addWidget(header)
        root.addWidget(splitter, 1)
        root.addWidget(status_bar)

        self.refresh_list()

    # ---------- 托盘 ----------
    def init_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.app_icon)
        self.tray.setToolTip(f"{__app_name__} - 停靠便签")

        tray_menu = QMenu()
        tray_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {CARD_COLOR};
                border: 1px solid {BORDER_COLOR};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
                color: {PRIMARY_TEXT};
            }}
            QMenu::item:selected {{ background-color: {SELECTED_BG}; }}
        """)

        show_action = QAction("展开 / 收起", self)
        show_action.triggered.connect(self.toggle_expand)
        tray_menu.addAction(show_action)

        edge_menu = tray_menu.addMenu("停靠位置")
        right_action = QAction("右侧", self)
        right_action.triggered.connect(lambda: self.set_edge("right"))
        left_action = QAction("左侧", self)
        left_action.triggered.connect(lambda: self.set_edge("left"))
        edge_menu.addAction(right_action)
        edge_menu.addAction(left_action)

        tray_menu.addSeparator()

        # 开机自启
        if autostart_supported():
            self.autostart_action = QAction("开机自启", self)
            self.autostart_action.setCheckable(True)
            self.autostart_action.setChecked(autostart_enabled())
            self.autostart_action.triggered.connect(self.toggle_autostart)
            tray_menu.addAction(self.autostart_action)

        tray_menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle_expand()

    def toggle_autostart(self):
        if self.autostart_action.isChecked():
            autostart_enable()
        else:
            autostart_disable()

    # ---------- 边缘检测 ----------
    def init_detect_timer(self):
        self.detect_timer = QTimer()
        self.detect_timer.setInterval(50)
        self.detect_timer.timeout.connect(self.check_mouse_edge)
        self.detect_timer.start()

        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.maybe_collapse)

    def check_mouse_edge(self):
        pos = QCursor.pos()
        screen = QApplication.primaryScreen().geometry()
        edge = self.config.get("edge", "right")

        near_edge = (
            pos.x() >= screen.width() - SCREEN_EDGE_MARGIN
            if edge == "right"
            else pos.x() <= SCREEN_EDGE_MARGIN
        )

        if not self.is_expanded:
            # 未展开：鼠标靠近边缘就展开
            if near_edge:
                self.expand()
        else:
            # 展开后 600ms 宽限期内不自动收起，防止闪屏
            if time.time() - self._expand_time < 0.6:
                return
            # 已展开：鼠标不在窗口内就启动收起计时
            if not self.geometry().contains(pos):
                if not self.hide_timer.isActive():
                    self.hide_timer.start(HIDE_DELAY_MS)
            else:
                # 鼠标回到窗口内，取消收起计时
                self.hide_timer.stop()

    def maybe_collapse(self):
        pos = QCursor.pos()
        if not self.geometry().contains(pos):
            self.collapse()

    # ---------- 窗口位置 ----------
    def align_to_edge(self):
        screen = QApplication.primaryScreen().availableGeometry()
        edge = self.config.get("edge", "right")
        y = screen.y()
        h = screen.height()
        if edge == "right":
            self.move(screen.width() - COLLAPSED_WIDTH, y)
        else:
            self.move(screen.x(), y)
        self.resize(COLLAPSED_WIDTH, h)

    def expand(self):
        if self.is_expanded:
            return
        self.is_expanded = True
        self._expand_time = time.time()
        screen = QApplication.primaryScreen().availableGeometry()
        edge = self.config.get("edge", "right")
        w = EXPANDED_WIDTH
        y = screen.y()
        h = screen.height()
        if edge == "right":
            self.move(screen.width() - w, y)
        else:
            self.move(screen.x(), y)
        self.resize(w, h)
        self.show()
        self.raise_()

    def collapse(self):
        if not self.is_expanded:
            return
        # 收纳前强制保存
        if self.edit_timer.isActive():
            self.edit_timer.stop()
            self.save_current_note()
        self.is_expanded = False
        screen = QApplication.primaryScreen().availableGeometry()
        edge = self.config.get("edge", "right")
        y = screen.y()
        h = screen.height()
        if edge == "right":
            self.move(screen.width() - COLLAPSED_WIDTH, y)
        else:
            self.move(screen.x(), y)
        self.resize(COLLAPSED_WIDTH, h)

    def toggle_expand(self):
        self.collapse() if self.is_expanded else self.expand()

    def set_edge(self, edge):
        self.config["edge"] = edge
        save_config(self.config)
        self.is_expanded = False
        self.align_to_edge()
        self.collapse()

    # ---------- 笔记操作 ----------
    def create_note(self):
        note = create_note(title="新笔记")
        self.notes.insert(0, note)
        save_notes(self.notes)
        self.refresh_list()
        self.select_note(note["id"])
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def delete_current_note(self):
        if not self.current_note_id:
            return
        note = self.find_note(self.current_note_id)
        if not note:
            return
        reply = QMessageBox.question(
            self, "删除笔记",
            f"确定删除「{note.get('title', '无标题')}」吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self.notes = [n for n in self.notes if n["id"] != self.current_note_id]
        self.current_note_id = None
        save_notes(self.notes)
        self.title_edit.blockSignals(True)
        self.title_edit.clear()
        self.title_edit.blockSignals(False)
        self.editor.blockSignals(True)
        self.editor.clear()
        self.editor.blockSignals(False)
        self.refresh_list()

    def show_list_context_menu(self, pos):
        item = self.note_list.itemAt(pos)
        if not item:
            return
        note_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background-color: {CARD_COLOR}; border: 1px solid {BORDER_COLOR}; padding: 4px; }}
            QMenu::item {{ padding: 6px 20px; border-radius: 4px; color: {PRIMARY_TEXT}; }}
            QMenu::item:selected {{ background-color: {SELECTED_BG}; }}
        """)
        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(lambda: self.rename_note(note_id))
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_note_by_id(note_id))
        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.exec(self.note_list.viewport().mapToGlobal(pos))

    def rename_note(self, note_id):
        note = self.find_note(note_id)
        if not note:
            return
        new_title, ok = QInputDialog.getText(
            self, "重命名", "笔记标题：", text=note.get("title", "")
        )
        if ok and new_title.strip():
            note["title"] = new_title.strip()
            from datetime import datetime
            note["updated_at"] = datetime.now().isoformat()
            save_notes(self.notes)
            self.refresh_list(keep_selection=True)

    def delete_note_by_id(self, note_id):
        note = self.find_note(note_id)
        if not note:
            return
        reply = QMessageBox.question(
            self, "删除笔记",
            f"确定删除「{note.get('title', '无标题')}」吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self.notes = [n for n in self.notes if n["id"] != note_id]
        if self.current_note_id == note_id:
            self.current_note_id = None
            self.title_edit.clear()
            self.editor.clear()
        save_notes(self.notes)
        self.refresh_list()

    def select_note(self, note_id):
        self.current_note_id = note_id
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item.data(Qt.UserRole) == note_id:
                self.note_list.setCurrentItem(item)
                break
        note = self.find_note(note_id)
        if note:
            self.title_edit.blockSignals(True)
            self.title_edit.setText(note.get("title", ""))
            self.title_edit.blockSignals(False)
            self.editor.blockSignals(True)
            self.editor.setPlainText(note.get("content", ""))
            self.editor.blockSignals(False)
            self.update_word_count()

    def on_note_selected(self, item):
        self.select_note(item.data(Qt.UserRole))

    def find_note(self, note_id):
        for n in self.notes:
            if n["id"] == note_id:
                return n
        return None

    def on_title_changed(self):
        self.save_indicator.setText("编辑中...")
        self.save_indicator.setStyleSheet(f"font-size: 10px; color: {ACCENT};")
        self.edit_timer.start(800)

    def on_text_changed(self):
        self.save_indicator.setText("编辑中...")
        self.save_indicator.setStyleSheet(f"font-size: 10px; color: {ACCENT};")
        self.update_word_count()
        self.edit_timer.start(800)

    def update_word_count(self):
        text = self.editor.toPlainText()
        # 统计中文字数 + 英文单词数
        chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english = len([w for w in text.split() if all(ord(c) < 128 for c in w)])
        total = chinese + english
        self.word_count_label.setText(f"{total} 字")

    def save_current_note(self):
        if not self.current_note_id:
            return
        note = self.find_note(self.current_note_id)
        if not note:
            return
        from datetime import datetime
        content = self.editor.toPlainText()
        title = self.title_edit.text().strip() or "无标题"
        note["content"] = content
        note["title"] = title
        note["updated_at"] = datetime.now().isoformat()
        save_notes(self.notes)
        self.save_indicator.setText("已保存")
        self.save_indicator.setStyleSheet(f"font-size: 10px; color: {SUCCESS};")
        self.refresh_list(keep_selection=True)

    def refresh_list(self, keep_selection=False):
        current_id = self.current_note_id
        keyword = self.search_box.text().strip().lower()
        self.note_list.clear()

        filtered = []
        for n in self.notes:
            if keyword:
                if keyword in n.get("title", "").lower() or keyword in n.get("content", "").lower():
                    filtered.append(n)
            else:
                filtered.append(n)

        filtered.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        for note in filtered:
            item = QListWidgetItem(self.note_list)
            item.setData(Qt.UserRole, note["id"])
            item.setSizeHint(QSize(0, 64))
            self.note_list.addItem(item)
            self.note_list.setItemWidget(item, NoteListItem(note))

        self.status_label.setText(f"{len(filtered)} 条笔记")

        if keep_selection and current_id:
            self.select_note(current_id)

    # ---------- 快捷键 ----------
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.New):
            self.create_note()
        elif event.matches(QKeySequence.Find):
            self.search_box.setFocus()
        elif event.matches(QKeySequence.Delete):
            self.delete_current_note()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        event.ignore()
        self.collapse()

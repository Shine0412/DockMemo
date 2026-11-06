"""主窗口"""
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QAction, QKeySequence, QCursor, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit, QPushButton,
    QSystemTrayIcon, QMenu, QLabel, QFrame, QSplitter, QStyle,
    QInputDialog, QMessageBox, QFileDialog
)

from . import __app_name__
from .styles import (
    EXPANDED_WIDTH, COLLAPSED_WIDTH, SCREEN_EDGE_MARGIN, HIDE_DELAY_MS,
    BG_COLOR, CARD_COLOR, BORDER_COLOR, PRIMARY_TEXT, SECONDARY_TEXT,
    MUTED_TEXT, ACCENT, ACCENT_HOVER, SELECTED_BG, DANGER, SUCCESS, HOVER_BG,
)
from .storage import load_notes, save_notes, load_config, save_config, create_note as make_note
from .widgets import NoteListItem
from .autostart import (
    is_supported as autostart_supported, is_enabled as autostart_enabled,
    enable as autostart_enable, disable as autostart_disable,
)

MENU_STYLE = f"""
    QMenu {{ background-color: {CARD_COLOR}; border: 1px solid {BORDER_COLOR}; padding: 4px; }}
    QMenu::item {{ padding: 6px 20px; border-radius: 4px; color: {PRIMARY_TEXT}; }}
    QMenu::item:selected {{ background-color: {SELECTED_BG}; }}
"""

SAVE_DEBOUNCE_MS = 800
EXPAND_GRACE_S = 0.6  # 展开后的宽限期，防止闪屏


class DockMemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.notes = load_notes()
        self.current_note_id = None
        self.is_expanded = False
        self._expand_time = 0  # 展开时间戳，用于宽限期
        self._quitting = False  # 是否正在退出（托盘退出流程）
        self._fullscreen = False  # 前台是否存在全屏程序
        self._fullscreen_prev_expanded = False  # 进入全屏前的展开状态
        self._order_cache = None  # 列表顺序缓存 (keyword, [note_ids])，编辑期间保持顺序稳定

        self.edit_timer = QTimer(self)
        self.edit_timer.setSingleShot(True)
        self.edit_timer.setInterval(SAVE_DEBOUNCE_MS)
        self.edit_timer.timeout.connect(self.save_current_note)

        self._load_icon()
        self.init_ui()
        self.init_tray()
        self.init_detect_timer()
        self.align_to_edge()

    # ---------- 图标 ----------
    def _load_icon(self):
        base = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(__file__).parent.parent
        icon_path = base / "assets" / "icon.ico"
        self.app_icon = (
            QIcon(str(icon_path)) if icon_path.exists()
            else self.style().standardIcon(QStyle.SP_ComputerIcon)
        )

    # ---------- UI ----------
    def init_ui(self):
        self.setWindowTitle(__app_name__)
        self.setWindowIcon(self.app_icon)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)

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

        # 标题行：收起按钮 + 应用名 + 保存状态 + 删除/新建
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
            QPushButton:hover {{ background-color: {HOVER_BG}; color: {PRIMARY_TEXT}; }}
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

        self.save_indicator = QLabel("已保存")
        self._set_save_indicator(True)
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
            QLineEdit:focus {{ border-color: {ACCENT}; background-color: {CARD_COLOR}; }}
        """)
        # 注意：textChanged 带有文本参数，必须用 lambda 吃掉，不能直接连 refresh_list
        self.search_box.textChanged.connect(lambda *_: self.refresh_list())
        header_layout.addWidget(self.search_box)

        # === 笔记列表 ===
        list_container = QFrame()
        list_container.setStyleSheet(f"background-color: {CARD_COLOR};")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        self.note_list = QListWidget()
        self.note_list.setStyleSheet(f"""
            QListWidget {{ border: none; background-color: {CARD_COLOR}; outline: none; }}
            QListWidget::item {{
                border-bottom: 1px solid {BORDER_COLOR};
                border-left: 3px solid transparent;
            }}
            QListWidget::item:selected {{
                background-color: {SELECTED_BG};
                border-left: 3px solid {ACCENT};
            }}
            QListWidget::item:hover {{ background-color: {HOVER_BG}; }}
        """)
        self.note_list.itemClicked.connect(self.on_note_selected)
        # 方向键/列表高亮变化时也切换笔记（不仅是鼠标点击）
        self.note_list.currentItemChanged.connect(self.on_current_item_changed)
        self.note_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.note_list.customContextMenuRequested.connect(self.show_list_context_menu)
        list_layout.addWidget(self.note_list)

        # === 编辑区 ===
        edit_container = QFrame()
        edit_container.setStyleSheet(f"background-color: {CARD_COLOR}; border-top: 1px solid {BORDER_COLOR};")
        edit_layout = QVBoxLayout(edit_container)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.setSpacing(0)

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
        self.title_edit.textChanged.connect(self._mark_dirty)
        edit_layout.addWidget(self.title_edit)

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
        tray_menu.setStyleSheet(MENU_STYLE)

        show_action = QAction("展开 / 收起", self)
        show_action.triggered.connect(self.toggle_expand)
        tray_menu.addAction(show_action)

        edge_menu = tray_menu.addMenu("停靠位置")
        for label, edge in (("右侧", "right"), ("左侧", "left")):
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, e=edge: self.set_edge(e))
            edge_menu.addAction(action)

        tray_menu.addSeparator()

        if autostart_supported():
            self.autostart_action = QAction("开机自启", self)
            self.autostart_action.setCheckable(True)
            self.autostart_action.setChecked(autostart_enabled())
            self.autostart_action.triggered.connect(self.toggle_autostart)
            tray_menu.addAction(self.autostart_action)

        tray_menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.toggle_expand()

    def toggle_autostart(self):
        checked = self.autostart_action.isChecked()
        ok = autostart_enable() if checked else autostart_disable()
        if not ok:  # 操作失败（如开发模式无 exe），回退勾选状态
            self.autostart_action.setChecked(not checked)

    def quit_app(self):
        """真正退出：落盘 → 隐藏托盘 → 关闭窗口 → 退出事件循环"""
        self._quitting = True
        self.flush_save()
        self.tray.hide()  # 先移除托盘图标，避免 Windows 上残留
        self.close()
        # 等托盘菜单的模态循环结束后再退出，确保进程真正结束
        QTimer.singleShot(0, QApplication.quit)

    # ---------- 边缘检测 ----------
    def init_detect_timer(self):
        self.detect_timer = QTimer(self)
        self.detect_timer.setInterval(50)
        self.detect_timer.timeout.connect(self.check_mouse_edge)
        self.detect_timer.start()

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.maybe_collapse)

        # 全屏程序检测：前台窗口全屏时隐藏自身，不挡在全屏程序前面
        self.fullscreen_timer = QTimer(self)
        self.fullscreen_timer.setInterval(300)
        self.fullscreen_timer.timeout.connect(self.check_fullscreen)
        self.fullscreen_timer.start()

    def _mouse_screen(self):
        """鼠标所在的屏幕，找不到时回退主屏"""
        pos = QCursor.pos()
        for screen in QApplication.screens():
            if screen.geometry().contains(pos):
                return screen
        return QApplication.primaryScreen()

    def _is_outer_edge(self, screen, edge):
        """只有虚拟桌面的最外侧边缘才算触发区，
        避免多屏拼接缝隙（如左屏右缘）误触发"""
        geos = [s.geometry() for s in QApplication.screens()]
        g = screen.geometry()
        if edge == "right":
            return g.right() == max(geo.right() for geo in geos)
        return g.left() == min(geo.left() for geo in geos)

    def check_mouse_edge(self):
        # 全屏程序在前台时不响应边缘（避免挡在全屏程序前面）
        if self._fullscreen:
            return
        pos = QCursor.pos()
        screen = self._mouse_screen()
        edge = self.config.get("edge", "right")
        if not self._is_outer_edge(screen, edge):
            return
        # 用 availableGeometry（不含任务栏），与窗口停靠位置保持同一基准
        geo = screen.availableGeometry()

        near_edge = (
            pos.x() >= geo.x() + geo.width() - SCREEN_EDGE_MARGIN
            if edge == "right"
            else pos.x() <= geo.x() + SCREEN_EDGE_MARGIN
        )

        if not self.is_expanded:
            if near_edge:
                self.expand()
        else:
            # 展开后宽限期内不自动收起，防止闪屏
            if time.time() - self._expand_time < EXPAND_GRACE_S:
                return
            # 鼠标不在窗口内就启动收起计时，回到窗口内则取消
            if not self.geometry().contains(pos):
                if not self.hide_timer.isActive():
                    self.hide_timer.start(HIDE_DELAY_MS)
            else:
                self.hide_timer.stop()

    def maybe_collapse(self):
        if not self.geometry().contains(QCursor.pos()):
            self.collapse()

    # ---------- 全屏检测 ----------
    def is_fullscreen_foreground(self):
        """前台窗口是否处于全屏状态（无边框且覆盖整个主屏）"""
        if sys.platform != "win32":
            return False
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd or int(self.winId()) == hwnd:
                return False
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            # 面板所在屏幕（Qt 全局坐标与 Win32 虚拟桌面坐标一致），
            # 多显示器时只关心挡住面板的那块屏
            geo = (self.screen() or QApplication.primaryScreen()).geometry()
            # 覆盖整块屏幕（含任务栏区域），排除普通最大化窗口
            covers_screen = (
                rect.left <= geo.x() and rect.top <= geo.y()
                and rect.right >= geo.x() + geo.width() - 1
                and rect.bottom >= geo.y() + geo.height() - 1
            )
            if not covers_screen:
                return False
            # 无标题栏/边框（WS_CAPTION = 0x00C00000），全屏游戏/视频均为无边框
            style = user32.GetWindowLongW(hwnd, -16)  # GWL_STYLE
            return not bool(style & 0x00C00000)
        except Exception:
            return False

    def check_fullscreen(self):
        """全屏程序出现时隐藏自身，退出全屏后恢复之前的状态"""
        fullscreen = self.is_fullscreen_foreground()
        if fullscreen == self._fullscreen:
            return
        self._fullscreen = fullscreen
        if fullscreen:
            self._fullscreen_prev_expanded = self.is_expanded
            if self.is_expanded:
                self.collapse()
            self.hide()
        elif self._fullscreen_prev_expanded:
            self.expand()
        else:
            self.show()
            self.align_to_edge()

    # ---------- 窗口位置 ----------
    def _apply_geometry(self, width):
        """把窗口停靠到「鼠标所在屏幕」配置的边缘，宽度为 width"""
        screen = self._mouse_screen().availableGeometry()
        if self.config.get("edge", "right") == "right":
            x = screen.x() + screen.width() - width
        else:
            x = screen.x()
        self.setGeometry(x, screen.y(), width, screen.height())

    def align_to_edge(self):
        self._apply_geometry(COLLAPSED_WIDTH)

    def expand(self):
        if self._fullscreen:
            # 全屏程序在前台时不弹出，但记住用户意图，退出全屏后恢复
            self._fullscreen_prev_expanded = True
            return
        if self.is_expanded:
            return
        self.is_expanded = True
        self._expand_time = time.time()
        self._apply_geometry(EXPANDED_WIDTH)
        self.show()
        self.raise_()

    def collapse(self):
        if not self.is_expanded:
            return
        self.flush_save()  # 收纳前落盘
        self.is_expanded = False
        self._apply_geometry(COLLAPSED_WIDTH)

    def toggle_expand(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def set_edge(self, edge):
        self.config["edge"] = edge
        save_config(self.config)
        self.is_expanded = False
        self.align_to_edge()

    # ---------- 编辑器读写 ----------
    def _set_editors(self, title, content):
        """加载内容到编辑器。仅在内容确实变化时才重写文本，
        避免 setText/setPlainText 重置光标、打断输入法组合。"""
        self.title_edit.blockSignals(True)
        if self.title_edit.text() != title:
            self.title_edit.setText(title)
        self.title_edit.blockSignals(False)
        self.editor.blockSignals(True)
        if self.editor.toPlainText() != content:
            self.editor.setPlainText(content)
        self.editor.blockSignals(False)
        self.update_word_count()

    def _mark_dirty(self):
        self._set_save_indicator(False)
        self.edit_timer.start()

    def _set_save_indicator(self, saved):
        text, color = ("已保存", SUCCESS) if saved else ("编辑中...", ACCENT)
        self.save_indicator.setText(text)
        self.save_indicator.setStyleSheet(f"font-size: 10px; color: {color};")

    def on_text_changed(self):
        self._mark_dirty()
        self.update_word_count()

    def update_word_count(self):
        text = self.editor.toPlainText()
        # 统计中文字数 + 英文单词数
        chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english = len([w for w in text.split() if all(ord(c) < 128 for c in w)])
        self.word_count_label.setText(f"{chinese + english} 字")

    def flush_save(self):
        """若防抖计时器在等待，立即落盘（切换/新建/删除/收起/退出前调用）"""
        if self.edit_timer.isActive():
            self.edit_timer.stop()
            self.save_current_note()

    def save_current_note(self):
        """落盘当前笔记。只更新数据和列表，绝不重写编辑器内容，
        这样自动保存不会移动光标、不会打断输入法。"""
        if not self.current_note_id:
            return
        note = self.find_note(self.current_note_id)
        if not note:
            return
        note["content"] = self.editor.toPlainText()
        note["title"] = self.title_edit.text().strip() or "无标题"
        note["updated_at"] = datetime.now().isoformat()
        save_notes(self.notes)
        self._set_save_indicator(True)
        # 可见集合未变时只就地更新当前项的文本，避免每次保存都重建整个列表
        if self._list_visible_set_matches():
            self._update_list_item(note)
        else:
            self.refresh_list()

    # ---------- 笔记操作 ----------
    def create_note(self):
        self.flush_save()  # 先落盘上一篇，避免未保存的编辑被覆盖
        note = make_note(title="新笔记")
        self.notes.insert(0, note)
        save_notes(self.notes)
        self.search_box.clear()  # 避免新笔记被搜索关键字过滤掉而"看起来丢失"
        self.refresh_list()
        self.select_note(note["id"])
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def delete_current_note(self):
        if self.current_note_id:
            self.delete_note_by_id(self.current_note_id)

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
        self.edit_timer.stop()
        self.notes = [n for n in self.notes if n["id"] != note_id]
        if self.current_note_id == note_id:
            self.current_note_id = None
            self._set_editors("", "")
        save_notes(self.notes)
        self.refresh_list()

    def select_note(self, note_id):
        """切换到指定笔记：先落盘当前笔记，再加载新笔记到编辑器"""
        if note_id != self.current_note_id:
            self.flush_save()
            self.current_note_id = note_id
            note = self.find_note(note_id)
            if note:
                self._set_editors(note.get("title", ""), note.get("content", ""))
            # 切换时重新按更新时间排序（刚编辑完的笔记升上去）
            self.refresh_list(force_resort=True)
        self._highlight_item(note_id)

    def _highlight_item(self, note_id):
        """仅同步列表的选中高亮，不触碰编辑器"""
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item.data(Qt.UserRole) == note_id:
                self.note_list.setCurrentItem(item)
                self.note_list.scrollToItem(item)
                break

    def on_note_selected(self, item):
        self.select_note(item.data(Qt.UserRole))

    def find_note(self, note_id):
        return next((n for n in self.notes if n["id"] == note_id), None)

    def _visible_note_ids(self):
        """按当前搜索关键字，应该可见的笔记 id 集合"""
        keyword = self.search_box.text().strip().lower()
        return {
            n["id"] for n in self.notes
            if not keyword
            or keyword in n.get("title", "").lower()
            or keyword in n.get("content", "").lower()
        }

    def _list_visible_set_matches(self):
        """列表里已渲染的笔记集合是否与应可见集合一致（一致则无需重建）"""
        current = {
            self.note_list.item(i).data(Qt.UserRole)
            for i in range(self.note_list.count())
        }
        return current == self._visible_note_ids()

    def _update_list_item(self, note):
        """就地更新某条笔记的列表项文本，不重建列表"""
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item.data(Qt.UserRole) == note["id"]:
                widget = self.note_list.itemWidget(item)
                if isinstance(widget, NoteListItem):
                    widget.set_note(note)
                return

    def refresh_list(self, force_resort: bool = False):
        """重建笔记列表（搜索过滤 + 排序），并保持当前项高亮。
        只动列表，不动编辑器——重写编辑器会导致光标跳动。
        force_resort=False 且可见集合未变时沿用上次顺序，
        避免编辑笔记时它反复跳到列表顶部。"""
        keyword = self.search_box.text().strip().lower()
        filtered = [
            n for n in self.notes
            if not keyword
            or keyword in n.get("title", "").lower()
            or keyword in n.get("content", "").lower()
        ]

        cache = self._order_cache
        cache_valid = (
            cache is not None
            and not force_resort
            and cache[0] == keyword
            and {n["id"] for n in filtered} == set(cache[1])
        )
        if cache_valid:
            order = {nid: i for i, nid in enumerate(cache[1])}
            filtered.sort(key=lambda n: order[n["id"]])
        else:
            filtered.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            self._order_cache = (keyword, [n["id"] for n in filtered])

        # 重建期间屏蔽信号：clear()/setCurrentItem 会同步派发
        # currentItemChanged，处理函数再操作列表会导致 C++ 层崩溃
        self.note_list.blockSignals(True)
        try:
            self.note_list.clear()
            for note in filtered:
                item = QListWidgetItem(self.note_list)
                item.setData(Qt.UserRole, note["id"])
                item.setSizeHint(QSize(0, 64))
                self.note_list.addItem(item)
                self.note_list.setItemWidget(item, NoteListItem(note))

            self.status_label.setText(f"{len(filtered)} 条笔记")
            if self.current_note_id:
                self._highlight_item(self.current_note_id)
        finally:
            self.note_list.blockSignals(False)

    def on_current_item_changed(self, current, previous):
        """列表高亮变化（方向键、点击）时加载对应笔记到编辑器"""
        if current is not None:
            self.select_note(current.data(Qt.UserRole))

    # ---------- 右键菜单 ----------
    def show_list_context_menu(self, pos):
        item = self.note_list.itemAt(pos)
        if not item:
            return
        note_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        export_action = QAction("导出为文件...", self)
        export_action.triggered.connect(lambda: self.export_note(note_id))
        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(lambda: self.rename_note(note_id))
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.delete_note_by_id(note_id))
        menu.addAction(export_action)
        menu.addSeparator()
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
        if not (ok and new_title.strip()):
            return
        note["title"] = new_title.strip()
        note["updated_at"] = datetime.now().isoformat()
        save_notes(self.notes)
        # 重命名的是当前打开的笔记时同步标题框，否则下次保存会把新名字覆盖回去
        if note_id == self.current_note_id:
            self.title_edit.blockSignals(True)
            self.title_edit.setText(note["title"])
            self.title_edit.blockSignals(False)
        # 重命名会更新 updated_at，按原行为重新排序
        self.refresh_list(force_resort=True)

    def export_note(self, note_id):
        """将单条笔记导出为 Markdown 或纯文本文件"""
        note = self.find_note(note_id)
        if not note:
            return
        title = note.get("title", "").strip() or "无标题"
        # 清理 Windows 文件名字符
        safe = re.sub(r'[\\/:*?"<>|]', "_", title).strip() or "无标题"
        path, selected_filter = QFileDialog.getSaveFileName(
            self, "导出笔记", str(Path.home() / f"{safe}.md"),
            "Markdown 文件 (*.md);;纯文本文件 (*.txt)"
        )
        if not path:
            return
        # 用户未带后缀时按所选过滤器补齐
        if path.lower().endswith(".txt"):
            fmt = "txt"
        elif path.lower().endswith(".md"):
            fmt = "md"
        else:
            fmt = "txt" if "纯文本" in selected_filter else "md"
            path += f".{fmt}"
        try:
            # newline="" 保持 LF，不随 Windows 转成 CRLF
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(self._format_export(note, fmt))
        except OSError as e:
            QMessageBox.warning(self, "导出失败", f"无法写入文件：\n{e}")
            return
        QMessageBox.information(self, "导出成功", f"已导出到：\n{path}")

    def _format_export(self, note, fmt):
        """构建导出文本：fmt = 'md' | 'txt'，统一 LF 换行"""
        title = note.get("title", "").strip() or "无标题"
        content = note.get("content", "").strip()
        created = self._format_time(note.get("created_at", ""))
        updated = self._format_time(note.get("updated_at", ""))
        if fmt == "txt":
            return (
                f"{title}\n{'=' * max(len(title), 4)}\n\n"
                f"创建于 {created} · 更新于 {updated}\n\n"
                f"{content or '（空笔记）'}\n"
            )
        return (
            f"# {title}\n\n"
            f"> 创建于 {created} · 更新于 {updated}\n\n"
            f"{content or '（空笔记）'}\n"
        )

    @staticmethod
    def _format_time(iso):
        """ISO 时间转为可读格式，解析失败时原样返回"""
        if not iso:
            return "未知"
        try:
            return datetime.fromisoformat(iso).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            return iso

    # ---------- 快捷键 ----------
    def keyPressEvent(self, event):
        focused = self.focusWidget()
        in_input = isinstance(focused, (QLineEdit, QTextEdit))
        if event.matches(QKeySequence.New):
            self.create_note()
        elif event.matches(QKeySequence.Find):
            self.search_box.setFocus()
        elif event.matches(QKeySequence.Delete) and not in_input:
            # 焦点在输入框时不删笔记（空编辑器/搜索框里按 Delete 会误触发）
            self.delete_current_note()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if self._quitting:
            event.accept()
        else:
            event.ignore()
            self.collapse()

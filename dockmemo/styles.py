"""配色与常量 - 支持深色/浅色主题，跟随系统"""
import sys
from pathlib import Path

# 路径
APP_DIR = Path.home() / ".dockmemo"
NOTES_FILE = APP_DIR / "notes.json"
CONFIG_FILE = APP_DIR / "config.json"

# 窗口尺寸
EXPANDED_WIDTH = 360
COLLAPSED_WIDTH = 6
SCREEN_EDGE_MARGIN = 12
HIDE_DELAY_MS = 50


def is_system_dark():
    """检测系统是否为深色模式（Windows）"""
    try:
        if sys.platform != "win32":
            return False
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return value == 0
    except Exception:
        return False


# 深色主题配色（贴近 Windows 11 暗色）
DARK = {
    "BG_COLOR": "#1b1b1b",
    "CARD_COLOR": "#2b2b2b",
    "BORDER_COLOR": "#3f3f3f",
    "PRIMARY_TEXT": "#ffffff",
    "SECONDARY_TEXT": "#b0b0b0",
    "MUTED_TEXT": "#7a7a7a",
    "ACCENT": "#667eea",
    "ACCENT_HOVER": "#7c8ff0",
    "SELECTED_BG": "#3a3a4a",
    "DANGER": "#ff6b6b",
    "DANGER_HOVER": "#ee5a5a",
    "SUCCESS": "#2ecc71",
    "HOVER_BG": "#333333",
}

# 浅色主题配色
LIGHT = {
    "BG_COLOR": "#f7f8fc",
    "CARD_COLOR": "#ffffff",
    "BORDER_COLOR": "#e2e8f0",
    "PRIMARY_TEXT": "#1e293b",
    "SECONDARY_TEXT": "#64748b",
    "MUTED_TEXT": "#94a3b8",
    "ACCENT": "#667eea",
    "ACCENT_HOVER": "#5a67d8",
    "SELECTED_BG": "#eef2ff",
    "DANGER": "#e53e3e",
    "DANGER_HOVER": "#c53030",
    "SUCCESS": "#10b981",
    "HOVER_BG": "#f8fafc",
}

# 根据系统主题选择配色
_theme = DARK if is_system_dark() else LIGHT

BG_COLOR = _theme["BG_COLOR"]
CARD_COLOR = _theme["CARD_COLOR"]
BORDER_COLOR = _theme["BORDER_COLOR"]
PRIMARY_TEXT = _theme["PRIMARY_TEXT"]
SECONDARY_TEXT = _theme["SECONDARY_TEXT"]
MUTED_TEXT = _theme["MUTED_TEXT"]
ACCENT = _theme["ACCENT"]
ACCENT_HOVER = _theme["ACCENT_HOVER"]
SELECTED_BG = _theme["SELECTED_BG"]
DANGER = _theme["DANGER"]
DANGER_HOVER = _theme["DANGER_HOVER"]
SUCCESS = _theme["SUCCESS"]
HOVER_BG = _theme["HOVER_BG"]

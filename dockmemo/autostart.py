"""开机自启管理（Windows 注册表）"""
import sys
import winreg

APP_NAME = "DockMemo"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_supported():
    return sys.platform == "win32"


def get_executable_path():
    """获取当前 exe 路径（打包后）"""
    if getattr(sys, "frozen", False):
        return sys.executable
    # 开发模式下不注册自启
    return None


def is_enabled():
    """检查是否已开启开机自启"""
    if not is_supported():
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable():
    """开启开机自启"""
    if not is_supported():
        return False
    exe_path = get_executable_path()
    if not exe_path:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def disable():
    """关闭开机自启"""
    if not is_supported():
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False

"""一键构建脚本：python build.py"""
import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"


def main():
    print("==> 清理旧构建...")
    for d in ["build", "dist"]:
        p = ROOT / d
        if p.exists():
            shutil.rmtree(p)
    spec = ROOT / "DockMemo.spec"
    if spec.exists():
        spec.unlink()

    print("==> 开始打包...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile", "--windowed",
        "--name", "DockMemo",
        "--icon", "assets/icon.ico",
        "--add-data", "assets;assets",
        "--collect-submodules", "dockmemo",
        "main.py",
    ]
    subprocess.run(cmd, check=True, cwd=ROOT)

    # 复制到根目录
    src = DIST / "DockMemo.exe"
    dst = ROOT / "DockMemo.exe"
    shutil.copy(src, dst)
    print(f"==> 完成: {dst} ({dst.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()

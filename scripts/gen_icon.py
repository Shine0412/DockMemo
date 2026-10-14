"""生成 DockMemo 应用图标 assets/icon.ico（纯 PySide6 + 手动 ICO 封装）"""
import sys
import struct
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, QByteArray
from PySide6.QtGui import QPainter, QPainterPath, QColor, QFont, QLinearGradient, QImage, QBrush
from PySide6.QtWidgets import QApplication


def render_icon_png(size=256):
    """渲染图标为 PNG bytes"""
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)

    margin = size * 0.06
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    radius = size * 0.24

    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)

    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0, QColor("#667eea"))
    gradient.setColorAt(1, QColor("#764ba2"))
    p.fillPath(path, QBrush(gradient))

    # 装饰：一条小横线代表"便签"
    p.setPen(QColor(255, 255, 255, 180))
    pen = p.pen()
    pen.setWidthF(size * 0.025)
    p.setPen(pen)
    line_y = rect.center().y() + size * 0.12
    line_w = size * 0.3
    p.drawLine(int(rect.center().x() - line_w / 2), int(line_y),
                int(rect.center().x() + line_w / 2), int(line_y))

    # M 字母
    font = QFont("Segoe UI", int(size * 0.38), QFont.Bold)
    p.setFont(font)
    p.setPen(QColor(255, 255, 255, 245))
    text_rect = QRectF(rect.x(), rect.y() - size * 0.04, rect.width(), rect.height() * 0.7)
    p.drawText(text_rect, Qt.AlignCenter, "M")

    p.end()

    from PySide6.QtCore import QBuffer, QIODevice
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    img.save(buffer, "PNG")
    return bytes(buffer.data())


def write_ico(png_bytes, sizes, output_path):
    """把多尺寸 PNG 封装成 .ico 文件"""
    # ICONDIR
    header = struct.pack("<HHH", 0, 1, len(sizes))

    entries = b""
    offset = 6 + 16 * len(sizes)

    for s, data in zip(sizes, png_bytes):
        w = s if s < 256 else 0
        h = s if s < 256 else 0
        entries += struct.pack(
            "<BBBBHHII",
            w, h, 0, 0,
            1, 32,
            len(data), offset
        )
        offset += len(data)

    body = b"".join(png_bytes)
    output_path.write_bytes(header + entries + body)


def main():
    app = QApplication(sys.argv)
    assets_dir = Path(__file__).parent / "assets"
    assets_dir.mkdir(exist_ok=True)

    sizes = [16, 24, 32, 48, 64, 128, 256]
    png_images = [render_icon_png(s) for s in sizes]

    ico_path = assets_dir / "icon.ico"
    write_ico(png_images, sizes, ico_path)
    print(f"Icon saved: {ico_path} ({ico_path.stat().st_size} bytes)")

    # 同时存一份 256px PNG 备用
    (assets_dir / "icon.png").write_bytes(png_images[-1])


if __name__ == "__main__":
    main()

# DockMemo

> 停靠在屏幕边缘的速记便签 —— 鼠标一靠就出来，写完就收回去。

[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6)](https://www.microsoft.com/windows)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 为什么做这个

临时想记点东西，不想开个新文件夹、不想建文件、不想找便签软件。
鼠标往屏幕边缘一靠，面板就出来，写完移开鼠标就收回去，像不存在一样。

## 功能

| 功能 | 说明 |
|---|---|
| **边缘停靠** | 默认收在屏幕右边缘，只露 6px 窄条 |
| **自动展开/收纳** | 鼠标靠近自动滑出，移开自动收回 |
| **始终置顶** | 浮在所有窗口前面 |
| **即写即存** | 输入自动保存，无需手动操作 |
| **标题编辑** | 每条笔记独立命名 |
| **全文搜索** | 标题 + 内容一起搜 |
| **删除/重命名** | 顶部按钮或右键菜单 |
| **字数统计** | 底部实时显示 |
| **主题跟随** | 自动适配 Windows 深色/浅色模式 |
| **开机自启** | 托盘菜单一键开关 |
| **纯本地** | 不联网、不收集数据 |

## 使用

1. 下载 `DockMemo.exe`
2. 双击运行
3. 鼠标移到屏幕最右侧，面板自动展开

> 如果 Windows SmartScreen 弹窗，点 **更多信息** → **仍要运行**。

### 快捷键

| 快捷键 | 功能 |
|---|---|
| `Ctrl + N` | 新建笔记 |
| `Ctrl + F` | 聚焦搜索 |
| `Delete` | 删除当前笔记 |

### 托盘菜单

右下角托盘图标右键：
- 展开 / 收起
- 停靠位置（左 / 右）
- 开机自启（勾选开关）
- 退出

## 数据存储

所有笔记保存在 `~/.dockmemo/notes.json`，纯 JSON 格式，随时可备份。

## 项目结构

```
DockMemo/
├── main.py               # 入口
├── build.py              # 一键打包脚本
├── dockmemo/             # 主包
│   ├── __main__.py       # 启动逻辑
│   ├── app.py            # 主窗口 + 交互
│   ├── storage.py        # 数据读写
│   ├── widgets.py        # 自定义控件
│   ├── styles.py         # 配色常量
│   └── autostart.py      # 开机自启
├── assets/
│   └── icon.ico
├── scripts/
│   └── gen_icon.py
├── requirements.txt
├── LICENSE
└── README.md
```

## 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py

# 打包成 exe
python build.py
```

## License

[MIT](LICENSE)

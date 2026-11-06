"""数据层：笔记与配置的读写"""
import json
import os
import uuid
from datetime import datetime

from .styles import APP_DIR, NOTES_FILE, CONFIG_FILE


def _atomic_write(path, data):
    """先写临时文件再原子替换，避免进程被杀/断电时截断损坏 JSON"""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_notes():
    """读取笔记；文件损坏时备份（带时间戳，不覆盖历史备份）而不是静默丢弃"""
    if not NOTES_FILE.exists():
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        bak = NOTES_FILE.with_name(
            f"notes.corrupt-{datetime.now():%Y%m%d-%H%M%S}.bak"
        )
        try:
            NOTES_FILE.rename(bak)
        except OSError:
            pass
        return []
    if not isinstance(data, list):
        return []
    # 补全字段、丢弃没有 id 的脏数据
    return [
        {
            "id": str(n["id"]),
            "title": str(n.get("title", "")),
            "content": str(n.get("content", "")),
            "created_at": str(n.get("created_at", "")),
            "updated_at": str(n.get("updated_at", "")),
        }
        for n in data
        if isinstance(n, dict) and n.get("id")
    ]


def save_notes(notes):
    _atomic_write(NOTES_FILE, notes)


def load_config():
    default = {"edge": "right", "always_on_top": True}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if isinstance(cfg, dict):
            cfg = {**default, **cfg}
            if cfg.get("edge") not in ("left", "right"):
                cfg["edge"] = default["edge"]
            return cfg
    except Exception:
        pass
    return default


def save_config(cfg):
    _atomic_write(CONFIG_FILE, cfg)


def create_note(title="新笔记", content=""):
    now = datetime.now().isoformat()
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": content,
        "created_at": now,
        "updated_at": now,
    }

"""learning-kb 共享逻辑:状态读写、内容寻址源登记、错误提示。"""
import argparse
import datetime
import hashlib
import importlib
import json
import shutil
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if _stream and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def now() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def read_json(p: Path):
    with open(p, "r", encoding="utf-8", newline="") as f:
        return json.load(f)


def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    tmp.replace(p)


def load_state(state_dir):
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)
    sp = state / "sources.json"
    stp = state / "status.json"
    sources = read_json(sp) if sp.exists() else {"version": 1, "sources": []}
    status = read_json(stp) if stp.exists() else {"stage": "brief", "sources": {}}
    return state, sources, status


def save_state(state_dir, sources, status):
    state = Path(state_dir)
    write_json(state / "sources.json", sources)
    write_json(state / "status.json", status)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def register(state_dir, kind, original_path, title=None, meta=None, content_bytes=None):
    """内容寻址登记。返回 (entry, is_duplicate)。"""
    state, sources, status = load_state(state_dir)
    p = Path(original_path)
    digest = sha256_of(p) if content_bytes is None else hashlib.sha256(content_bytes).hexdigest()
    for s in sources["sources"]:
        if s["sha256"] == digest:
            return s, True
    ext = p.suffix.lstrip(".").lower() or kind
    stored = state / "sources" / f"{digest[:12]}.{ext}"
    sid = f"src_{len(sources['sources']) + 1:04d}"
    while any(s["id"] == sid for s in sources["sources"]):
        sid = f"src_{int(sid[4:]) + 1:04d}"
    stored.parent.mkdir(parents=True, exist_ok=True)
    if content_bytes is not None:
        stored.write_bytes(content_bytes)
    else:
        shutil.copy2(p, stored)
    entry = {
        "id": sid, "kind": kind, "sha256": digest,
        "original_path": str(p), "stored_file": f"sources/{stored.name}",
        "title": title or p.stem, "meta": meta or {},
        "status": "registered", "created_at": now(), "updated_at": now(),
    }
    sources["sources"].append(entry)
    status["sources"][sid] = "registered"
    save_state(state_dir, sources, status)
    return entry, False


def update_source(state_dir, sid, **fields):
    _, sources, status = load_state(state_dir)
    for s in sources["sources"]:
        if s["id"] == sid:
            s.update(fields)
            s["updated_at"] = now()
            if "status" in fields:
                status["sources"][sid] = fields["status"]
            save_state(state_dir, sources, status)
            return s
    sys.exit(f"错误:未知来源 id {sid}")


def need(module_name, pip_name=None):
    """惰性导入依赖;缺失时给出修复提示。"""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        hint = f"缺少依赖 {pip_name or module_name}。运行一次:\n" \
               f"  powershell -NoProfile -File <skill>/scripts/setup.ps1\n" \
               f"或直接:\n  uv pip install {pip_name or module_name}"
        sys.exit(hint)


def base_argparser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--state", required=True, help=".learning-kb 状态目录")
    return p


def flatten(values):
    """--input a b c(--input 可重复)统一拍平成列表。"""
    return [v for group in values for v in (group if isinstance(group, list) else [group])]


def remove_source(state_dir, sid):
    """登记后转换失败时回滚登记,保证失败文件可重试。"""
    _, sources, status = load_state(state_dir)
    sources["sources"] = [s for s in sources["sources"] if s["id"] != sid]
    status["sources"].pop(sid, None)
    save_state(state_dir, sources, status)


def run_batch(items, fn, label="文件"):
    """逐项执行,单项失败不中断批次;有失败返回 1,否则 0。
    SystemExit(如缺依赖)直接向上传播,不吞。"""
    failed = 0
    for it in items:
        try:
            fn(it)
        except Exception as e:  # noqa: BLE001 - 批次模式,单项失败继续
            print(f"[失败] {it}: {e}")
            failed += 1
    if failed:
        print(f"[批次] {failed}/{len(items)} 个{label}失败")
    return 1 if failed else 0

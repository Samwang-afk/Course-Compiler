"""压测:体量、unicode、损坏文件混合批次、重复投递。"""
import subprocess
import sys
import time
from pathlib import Path

import pytest

import chat2md
import common
import parse_ir
import pdf2md
from conftest import SCRIPTS, load_sources, make_chat, make_pdf

pytestmark = pytest.mark.stress

UNICODE_NAMES = [
    "材料 №1(测试).txt", "笔记 😀 带表情.txt", "材料 with spaces & symbols!.txt",
    "繁体筆記-001.txt", "混合Mixed命名-①②③.txt",
]


def _ingest_chat_batch(state, materials, n, base_content="老师:知识点{i}:内容{i}"):
    files = []
    Path(materials).mkdir(parents=True, exist_ok=True)
    for i in range(n):
        f = materials / f"chat_{i:03d}.txt"
        files.append(make_chat(f, [f"2026-08-0{i % 9 + 1} 10:00 老师",
                                   base_content.format(i=i)]))
    for f in files:
        chat2md.convert_one(state, f, "chat")
    return files


class TestVolume:
    def test_many_sources_ingest_parse(self, state_with_brief, materials):
        n_chat = 80
        n_pdf = 20
        t0 = time.time()
        _ingest_chat_batch(state_with_brief, materials, n_chat)
        for i in range(n_pdf):
            p = make_pdf(materials / f"pdf_{i:03d}.pdf",
                         [(f"第{i}章", f"这是第{i}章的内容。")])
            pdf2md.convert_one(state_with_brief, p)
        todo = [s["id"] for s in load_sources(state_with_brief)
                if s["status"] in ("registered", "extracted")]
        assert len(todo) == n_chat + n_pdf
        for sid in todo:
            parse_ir.parse_one(state_with_brief, sid)
        elapsed = time.time() - t0
        sources = load_sources(state_with_brief)
        assert len(sources) == n_chat + n_pdf
        assert all(s["status"] == "parsed" for s in sources)
        docs = list((Path(state_with_brief) / "ir" / "documents").glob("*.json"))
        assert len(docs) == n_chat + n_pdf
        assert elapsed < 120, f"太慢: {elapsed:.1f}s"

    def test_mass_duplicates_zero_growth(self, state_with_brief, materials):
        _ingest_chat_batch(state_with_brief, materials, 50)
        before = len(load_sources(state_with_brief))
        # 同样内容再投 50 次(换文件名)
        _ingest_chat_batch(state_with_brief, materials / "dup", 50)
        assert len(load_sources(state_with_brief)) == before


class TestUnicode:
    def test_unicode_filenames_and_content(self, state_with_brief, materials):
        for i, name in enumerate(UNICODE_NAMES):
            f = materials / name
            f.write_text(
                f"2026-01-0{i % 9 + 1} 12:00 老师\n"
                f"知识点:混合内容 😀 中文 English 数字123\n"
                f"长行: {'x' * 5000}\n",
                encoding="utf-8")
            chat2md.convert_one(state_with_brief, f, "chat")
        sources = load_sources(state_with_brief)
        assert len(sources) == len(UNICODE_NAMES)
        for s in sources:
            md = open(f"{state_with_brief}/{s['extracted_file']}",
                      encoding="utf-8").read()
            assert "😀" in md
            assert "中文 English" in md

    def test_unicode_roundtrip_through_ir(self, state_with_brief, materials):
        f = materials / "中文 😀.txt"
        f.write_text("2026-01-01 08:00 甲\n内容:αβγ ✓ 完成\n", encoding="utf-8")
        chat2md.convert_one(state_with_brief, f, "chat")
        parse_ir.parse_one(state_with_brief, "src_0001")
        ir = common.read_json(Path(state_with_brief) / "ir" / "documents" / "src_0001.json")
        text = "\n".join(b["text"] for b in ir["blocks"])
        assert "αβγ" in text and "✓" in text


class TestMixedBatch:
    def test_corrupt_files_in_large_batch(self, state_with_brief, materials):
        """100 个文件混入 10 个损坏文件:批次继续,好文件全部入库,退出码 1。"""
        goods = []
        for i in range(90):
            f = materials / f"g_{i:03d}.txt"
            f.write_text(f"2026-01-01 10:00 A\n内容 {i}\n", encoding="utf-8")
            goods.append(str(f))
        bads = []
        for i in range(10):
            b = materials / f"bad_{i:03d}.pdf"
            b.write_bytes(b"garbage-not-a-pdf" * 20)
            bads.append(str(b))
        r1 = subprocess.run(
            [sys.executable, str(SCRIPTS / "chat2md.py"), "--state",
             state_with_brief, "--input", *goods],
            capture_output=True, text=True, encoding="utf-8", timeout=300)
        r2 = subprocess.run(
            [sys.executable, str(SCRIPTS / "pdf2md.py"), "--state",
             state_with_brief, "--input", *bads],
            capture_output=True, text=True, encoding="utf-8", timeout=300)
        assert r1.returncode == 0
        assert r2.returncode == 1
        assert "[批次]" in r2.stdout
        assert len(load_sources(state_with_brief)) == 90

    def test_batch_performance_single_script(self, state_with_brief, materials):
        goods = []
        for i in range(200):
            f = materials / f"p_{i:03d}.txt"
            f.write_text(f"2026-01-01 10:00 A\n内容 {i}\n", encoding="utf-8")
            goods.append(str(f))
        t0 = time.time()
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "chat2md.py"), "--state",
             state_with_brief, "--input", *goods],
            capture_output=True, text=True, encoding="utf-8", timeout=300)
        elapsed = time.time() - t0
        assert r.returncode == 0, r.stdout[-500:]
        assert len(load_sources(state_with_brief)) == 200
        assert elapsed < 60, f"200 文件耗时 {elapsed:.1f}s"

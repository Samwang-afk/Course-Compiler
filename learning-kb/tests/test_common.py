"""common.py:状态读写、内容寻址登记、去重、批次容错。"""
import json
import sys
from pathlib import Path

import pytest

import common


class TestRegister:
    def test_new_source(self, state, materials):
        f = materials / "a.txt"
        f.write_text("hello", encoding="utf-8")
        entry, dup = common.register(state, "txt", f)
        assert not dup
        assert entry["id"] == "src_0001"
        assert entry["kind"] == "txt"
        assert entry["status"] == "registered"
        stored = Path(state) / "sources" / f"{entry['sha256'][:12]}.txt"
        assert stored.read_bytes() == b"hello"

    def test_duplicate_returns_existing(self, state, materials):
        a = materials / "a.txt"
        a.write_text("same content", encoding="utf-8")
        b = materials / "b.txt"
        b.write_text("same content", encoding="utf-8")
        e1, d1 = common.register(state, "txt", a)
        e2, d2 = common.register(state, "txt", b)
        assert not d1 and d2
        assert e1["id"] == e2["id"]
        assert len(common.load_state(state)[1]["sources"]) == 1

    def test_content_bytes_registration(self, state):
        entry, dup = common.register(state, "url", Path("https://example.com/x"),
                                     title="网页", content_bytes="<html>hi</html>".encode())
        assert not dup
        assert entry["title"] == "网页"

    def test_update_source_and_status(self, state, materials):
        f = materials / "a.txt"
        f.write_text("x", encoding="utf-8")
        entry, _ = common.register(state, "txt", f)
        common.update_source(state, entry["id"], status="parsed", meta={"pages": 3})
        got = common.load_state(state)[1]["sources"][0]
        assert got["status"] == "parsed"
        assert got["meta"]["pages"] == 3
        assert common.load_state(state)[2]["sources"][entry["id"]] == "parsed"

    def test_update_unknown_source_exits(self, state):
        with pytest.raises(SystemExit):
            common.update_source(state, "src_9999", status="parsed")

    def test_ids_never_reused_after_fail(self, state, materials):
        # 连续登记,id 递增且唯一
        ids = []
        for i in range(5):
            f = materials / f"f{i}.txt"
            f.write_text(f"content-{i}", encoding="utf-8")
            e, _ = common.register(state, "txt", f)
            ids.append(e["id"])
        assert len(set(ids)) == 5
        assert ids == [f"src_{i:04d}" for i in range(1, 6)]


class TestStateRoundtrip:
    def test_json_roundtrip_unicode(self, state):
        common.write_json(Path(state) / "x.json", {"文本": "中文😀", "n": [1, 2]})
        back = common.read_json(Path(state) / "x.json")
        assert back["文本"] == "中文😀"
        # 无 BOM、无 CRLF
        raw = (Path(state) / "x.json").read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert b"\r\n" not in raw

    def test_load_state_creates_defaults(self, state):
        _, sources, status = common.load_state(state)
        assert sources == {"version": 1, "sources": []}
        assert status["stage"] == "brief"


class TestRunBatch:
    def test_all_ok(self, capsys):
        assert common.run_batch([1, 2, 3], lambda x: None) == 0

    def test_failures_isolated_and_counted(self, capsys):
        def fn(x):
            if x == 2:
                raise ValueError("boom")
        code = common.run_batch([1, 2, 3], fn)
        out = capsys.readouterr().out
        assert code == 1
        assert "boom" in out
        assert "1/3" in out

    def test_systemexit_propagates(self):
        def fn(x):
            sys.exit("fatal")
        with pytest.raises(SystemExit):
            common.run_batch([1], fn)

    def test_batch_imports_without_deps_error(self, state):
        # need() 缺失依赖时 SystemExit 且带安装提示
        with pytest.raises(SystemExit) as ei:
            common.need("definitely_missing_module_xyz", "definitely-missing")
        assert "setup.ps1" in str(ei.value)

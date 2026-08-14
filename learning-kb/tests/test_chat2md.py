"""chat2md.py:聊天导出与表格转换。"""
import json

import chat2md
from conftest import get_source, load_sources


class TestChatFormat:
    def test_chat_lines(self, state, materials):
        f = materials / "chat.txt"
        f.write_text(
            "2026-08-10 21:03 小明\n最近在学 asyncio\n\n"
            "2026-08-10 21:05 老师\n一句话:协程是能暂停恢复的函数\n",
            encoding="utf-8")
        chat2md.convert_one(state, f, "chat")
        src = get_source(state, "src_0001")
        md = open(src["extracted_file"] and f"{state}/{src['extracted_file']}",
                  encoding="utf-8").read()
        assert "**小明**" in md and "**老师**" in md
        assert "<!-- time:21:03 -->" in md

    def test_chat_without_timestamp_falls_back_to_plain(self, state, materials):
        f = materials / "chat.txt"
        f.write_text("没有时间戳的一行\n", encoding="utf-8")
        chat2md.convert_one(state, f, "chat")
        src = get_source(state, "src_0001")
        md = open(f"{state}/{src['extracted_file']}", encoding="utf-8").read()
        assert "没有时间戳的一行" in md

    def test_duplicate_skipped(self, state, materials):
        f = materials / "chat.txt"
        f.write_text("2026-08-10 21:03 小明\nhi\n", encoding="utf-8")
        chat2md.convert_one(state, f, "chat")
        chat2md.convert_one(state, f, "chat")
        assert len(load_sources(state)) == 1


class TestTableFormat:
    def test_csv(self, state, materials):
        f = materials / "t.csv"
        f.write_text("name,score\nalice,90\nbob,85\n", encoding="utf-8")
        chat2md.convert_one(state, f, "table")
        src = get_source(state, "src_0001")
        md = open(f"{state}/{src['extracted_file']}", encoding="utf-8").read()
        assert "| name | score |" in md
        assert "| alice | 90 |" in md

    def test_tsv(self, state, materials):
        f = materials / "t.tsv"
        f.write_text("名称\t数值\n甲\t1\n", encoding="utf-8")
        chat2md.convert_one(state, f, "table")
        md = open(f"{state}/extracted/src_0001.md", encoding="utf-8").read()
        assert "| 名称 | 数值 |" in md

    def test_json_list_of_objects(self, state, materials):
        f = materials / "t.json"
        f.write_text(json.dumps([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]), encoding="utf-8")
        chat2md.convert_one(state, f, "table")
        md = open(f"{state}/extracted/src_0001.md", encoding="utf-8").read()
        assert "| a | b |" in md and "| 2 | y |" in md

    def test_pipe_escaped_in_cell(self, state, materials):
        f = materials / "t.csv"
        f.write_text('name,note\n"a","x|y"\n', encoding="utf-8")
        chat2md.convert_one(state, f, "table")
        md = open(f"{state}/extracted/src_0001.md", encoding="utf-8").read()
        assert "x\\|y" in md


class TestAuto:
    def test_auto_detects_chat(self, state, materials):
        f = materials / "auto.txt"
        f.write_text("2026-01-01 10:00 张三\n你好\n", encoding="utf-8")
        chat2md.convert_one(state, f, "auto")
        src = get_source(state, "src_0001")
        assert src["kind"] == "chat"
        assert src["meta"]["format"] == "chat"

    def test_auto_detects_table(self, state, materials):
        f = materials / "auto.csv"
        f.write_text("a,b\n1,2\n", encoding="utf-8")
        chat2md.convert_one(state, f, "auto")
        src = get_source(state, "src_0001")
        assert src["kind"] == "table"

"""端到端:真实脚本(ingest/parse/qa/commit)+ 模拟 LLM(extract/merge/link/compile)跑全管线。"""
from pathlib import Path

import chat2md
import commit
import pdf2md
import parse_ir
import qa_check
from conftest import (compile_notes, get_source, make_chat, make_pdf,
                      merge_proposals, write_proposal)

BODIES = {
    "k_coroutine": {"title": "协程是什么", "detail": "协程是可暂停恢复的函数。"},
    "k_await": {"title": "await 与挂起", "detail": "await 挂起协程等待完成。"},
    "k_event_loop": {"title": "事件循环", "detail": "事件循环负责调度协程。"},
}
TOPICS = [
    {"topic": "协程基础", "path": "asyncio/协程基础", "items": ["k_coroutine", "k_await"]},
    {"topic": "调度机制", "path": "asyncio/调度机制", "items": ["k_event_loop"]},
]


def _full_first_run(state, materials):
    """ingest 2 聊天 + 1 PDF -> parse -> 模拟 extract/merge/compile -> qa -> commit。"""
    chat1 = make_chat(materials / "chat1.txt",
                      ["2026-08-01 10:00 小明", "协程是什么?", "",
                       "2026-08-01 10:01 老师", "协程是能暂停和恢复的函数。"])
    chat2 = make_chat(materials / "chat2.txt",
                      ["2026-08-02 10:00 小红", "await 的作用是?",
                       "2026-08-02 10:01 老师", "await 挂起协程等待完成。"])
    pdf = make_pdf(materials / "notes.pdf",
                   [("事件循环", "事件循环负责调度所有协程。")])
    chat2md.convert_one(state, chat1, "chat")
    chat2md.convert_one(state, chat2, "chat")
    pdf2md.convert_one(state, pdf)
    parse_ir.parse_one(state, "src_0001")
    parse_ir.parse_one(state, "src_0002")
    parse_ir.parse_one(state, "src_0003")

    write_proposal(state, "src_0001", [{
        "id": "k_coroutine", "type": "concept", "title": "协程是什么",
        "detail": "协程是能暂停和恢复的函数。",
        "sources": [{"src_id": "src_0001", "block": "b2", "ref": "time:10:01"}],
        "tags": ["t"], "links": [], "status": "proposed"}])
    write_proposal(state, "src_0002", [{
        "id": "k_await", "type": "concept", "title": "await 与挂起",
        "detail": "await 挂起协程等待完成。",
        "sources": [{"src_id": "src_0002", "block": "b2", "ref": "time:10:01"}],
        "tags": ["t"], "links": [], "status": "proposed"}])
    write_proposal(state, "src_0003", [{
        "id": "k_event_loop", "type": "concept", "title": "事件循环",
        "detail": "事件循环负责调度协程。",
        "sources": [{"src_id": "src_0003", "block": "b1", "ref": "page:1"}],
        "tags": ["t"], "links": [], "status": "proposed"}])
    merge_proposals(state)
    compile_notes(state, TOPICS, BODIES)

    issues, n_notes, n_items = qa_check.check(state)
    assert issues == [], issues
    assert n_items == 3
    commit.cmd_commit(state)
    return Path(state).parent


class TestFullPipeline:
    def test_first_run_end_to_end(self, state_with_brief, materials):
        vault = _full_first_run(state_with_brief, materials)
        assert (vault / "asyncio" / "协程基础.md").exists()
        assert (vault / "asyncio" / "调度机制.md").exists()
        assert (vault / "Start Here.md").exists()
        note = (vault / "asyncio" / "协程基础.md").read_text(encoding="utf-8")
        assert "协程是可暂停恢复的函数。" in note
        assert "await 挂起协程等待完成。" in note
        assert "[[asyncio/调度机制]]" in note
        start = (vault / "Start Here.md").read_text(encoding="utf-8")
        assert "[[asyncio/协程基础]]" in start

    def test_reingest_duplicates_zero_change(self, state_with_brief, materials):
        vault = _full_first_run(state_with_brief, materials)
        from conftest import load_sources
        before = len(load_sources(state_with_brief))
        # 重新投递同样内容
        chat = make_chat(materials / "dup-chat.txt",
                         ["2026-08-01 10:00 小明", "协程是什么?", "",
                          "2026-08-01 10:01 老师", "协程是能暂停和恢复的函数。"])
        chat2md.convert_one(state_with_brief, chat, "chat")
        assert len(load_sources(state_with_brief)) == before
        # 知识文件无变化
        k_before = (Path(state_with_brief) / "ir" / "knowledge.json").read_bytes()
        merge_proposals(state_with_brief)
        assert (Path(state_with_brief) / "ir" / "knowledge.json").read_bytes() == k_before

    def test_rollback_then_recommit(self, state_with_brief, materials):
        vault = _full_first_run(state_with_brief, materials)
        run = sorted((Path(state_with_brief) / "runs").glob("run_*.json"))[-1].stem
        commit.cmd_rollback(state_with_brief, run)
        assert not (vault / "Start Here.md").exists()
        assert not (vault / "asyncio" / "协程基础.md").exists()
        commit.cmd_commit(state_with_brief)
        assert (vault / "Start Here.md").exists()

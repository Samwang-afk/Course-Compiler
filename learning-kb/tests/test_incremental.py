"""增量更新:新增材料只影响受影响笔记,用户手写区保留。"""
from pathlib import Path

import chat2md
import commit
import parse_ir
import qa_check
from conftest import (compile_notes, make_chat, merge_proposals,
                      write_proposal)
from test_pipeline_e2e import BODIES, TOPICS, _full_first_run

BODIES2 = dict(BODIES, **{
    "k_semaphore": {"title": "Semaphore 限流",
                    "detail": "asyncio.Semaphore(n) 限制同时运行的协程数。"},
})
TOPICS2 = [dict(TOPICS[0]), dict(TOPICS[1], items=["k_event_loop", "k_semaphore"])]


class TestIncremental:
    def test_incremental_update_preserves_user_edits(self, state_with_brief, materials):
        vault = _full_first_run(state_with_brief, materials)

        # 用户在「受影响」和「未受影响」笔记里都加了手写内容
        affected = vault / "asyncio" / "调度机制.md"
        affected.write_text(affected.read_text(encoding="utf-8")
                            + "\n## 我的补充\n\n用户手写内容A\n", encoding="utf-8")
        unaffected = vault / "asyncio" / "协程基础.md"
        unaffected.write_text(unaffected.read_text(encoding="utf-8")
                              + "\n## 我的笔记\n\n用户手写内容B\n", encoding="utf-8")
        unaffected_before = unaffected.read_bytes()

        # 新聊天材料:带来新概念 k_semaphore
        chat = make_chat(materials / "new-chat.txt",
                         ["2026-08-05 20:00 老师",
                          "asyncio.Semaphore(n) 限制同时运行的协程数量。"])
        chat2md.convert_one(state_with_brief, chat, "chat")
        src = next(s for s in __import__("conftest").load_sources(state_with_brief)
                   if s["title"] == "new-chat")
        parse_ir.parse_one(state_with_brief, src["id"])
        write_proposal(state_with_brief, src["id"], [{
            "id": "k_semaphore", "type": "concept", "title": "Semaphore 限流",
            "detail": "asyncio.Semaphore(n) 限制同时运行的协程数。",
            "sources": [{"src_id": src["id"], "block": "b1", "ref": "time:20:00"}],
            "tags": ["t"], "links": [], "status": "proposed"}])
        merge_proposals(state_with_brief)
        compile_notes(state_with_brief, TOPICS2, BODIES2)

        issues, _, _ = qa_check.check(state_with_brief)
        assert issues == [], issues
        commit.cmd_commit(state_with_brief)

        # 受影响笔记:新内容 + 用户手写保留
        affected_text = affected.read_text(encoding="utf-8")
        assert "Semaphore" in affected_text
        assert "用户手写内容A" in affected_text
        # 未受影响笔记:逐字节一致(用户手写保留)
        assert unaffected.read_bytes() == unaffected_before

    def test_second_material_reuses_stable_ids(self, state_with_brief, materials):
        vault = _full_first_run(state_with_brief, materials)
        # 新聊天再次讲到协程 → 同 id k_coroutine,merge 后应只有 3 个条目且来源合并
        chat = make_chat(materials / "again.txt",
                         ["2026-08-06 20:00 老师",
                          "补充:协程是 async def 定义的函数。"])
        chat2md.convert_one(state_with_brief, chat, "chat")
        src = next(s for s in __import__("conftest").load_sources(state_with_brief)
                   if s["title"] == "again")
        parse_ir.parse_one(state_with_brief, src["id"])
        write_proposal(state_with_brief, src["id"], [{
            "id": "k_coroutine", "type": "concept", "title": "协程是什么",
            "detail": "协程是 async def 定义、可暂停恢复的函数。",
            "sources": [{"src_id": src["id"], "block": "b1", "ref": "time:20:00"}],
            "tags": ["t"], "links": [], "status": "proposed"}])
        items = merge_proposals(state_with_brief)
        assert len(items) == 3                       # 未新增条目
        k = next(i for i in items if i["id"] == "k_coroutine")
        assert len(k["sources"]) == 2                # 来源合并
        assert "async def" in k["detail"]            # 内容更新

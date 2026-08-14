"""commit.py + qa_check.py:managed 区域合并、提交、回滚、QA。"""
import json
from pathlib import Path

import commit
import qa_check
from conftest import compile_notes, load_sources


def write_staged(state, rel, text):
    p = Path(state) / "staging" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


MANAGED_NEW = (
    '---\ntitle: "测试"\ntags: [t]\nlkb-generated: true\n---\n\n'
    '<!-- lkb-managed:start -->\n# 测试\n\n新生成正文\n<!-- lkb-managed:end -->\n')


class TestMergeManaged:
    def test_user_edits_survive(self):
        old = (MANAGED_NEW
               + "\n## 我的笔记\n\n用户手写,必须保留\n")
        new = MANAGED_NEW.replace("新生成正文", "更新后的正文 v2")
        merged = commit.merge_managed(new, old)
        assert "更新后的正文 v2" in merged
        assert "## 我的笔记" in merged
        assert "用户手写,必须保留" in merged

    def test_frontmatter_replaced(self):
        old = (MANAGED_NEW.replace("tags: [t]", "tags: [old-tag]")
               + "\n## 我的笔记\n\n用户内容\n")
        new = MANAGED_NEW.replace("tags: [t]", "tags: [new-tag]")
        merged = commit.merge_managed(new, old)
        assert "tags: [new-tag]" in merged
        assert "old-tag" not in merged
        assert "用户内容" in merged

    def test_user_edits_inside_managed_region_are_generated_territory(self):
        # 用户写在 managed 区域内属于生成区,更新时会被覆盖(设计行为)
        old = (MANAGED_NEW.replace("新生成正文", "新生成正文\n\n用户误写在生成区")
               + "\n用户区内容\n")
        new = MANAGED_NEW
        merged = commit.merge_managed(new, old)
        assert "用户误写在生成区" not in merged
        assert "用户区内容" in merged

    def test_no_markers_falls_back_to_new(self):
        old = "普通文件,无标记\n"
        new = "全新内容\n"
        assert commit.merge_managed(new, old) == new


class TestCommitRollback:
    def test_commit_creates_files_and_manifest(self, state):
        write_staged(state, "主题/笔记.md", MANAGED_NEW)
        write_staged(state, "Start Here.md", MANAGED_NEW)
        commit.cmd_commit(state)
        vault = Path(state).parent
        assert (vault / "主题" / "笔记.md").exists()
        assert (vault / "Start Here.md").exists()
        runs = list((Path(state) / "runs").glob("run_*.json"))
        assert len(runs) == 1
        manifest = json.loads(runs[0].read_text(encoding="utf-8"))
        assert len(manifest["actions"]) == 2

    def test_update_backs_up_and_merges(self, state):
        write_staged(state, "n.md", MANAGED_NEW)
        commit.cmd_commit(state)
        vault = Path(state).parent
        # 用户手写 + 新版本 staging
        (vault / "n.md").write_text(
            MANAGED_NEW + "\n## 用户补充\n\n手写\n", encoding="utf-8")
        write_staged(state, "n.md", MANAGED_NEW.replace("新生成正文", "v2"))
        commit.cmd_commit(state)
        text = (vault / "n.md").read_text(encoding="utf-8")
        assert "v2" in text and "## 用户补充" in text and "手写" in text

    def test_rollback_restores_and_removes(self, state):
        write_staged(state, "n.md", MANAGED_NEW)
        write_staged(state, "fresh.md", MANAGED_NEW)
        commit.cmd_commit(state)
        vault = Path(state).parent
        runs = sorted((Path(state) / "runs").glob("run_*.json"))
        run1 = runs[0].stem
        # 第二次提交:更新 n.md、删除 fresh.md(从 staging 移除即不再提交,模拟删除)
        write_staged(state, "n.md", MANAGED_NEW.replace("新生成正文", "v2"))
        (Path(state) / "staging" / "fresh.md").unlink()
        commit.cmd_commit(state)
        run2 = sorted((Path(state) / "runs").glob("run_*.json"))[-1].stem
        assert "v2" in (vault / "n.md").read_text(encoding="utf-8")
        # 回滚 run2:n.md 恢复 v1
        commit.cmd_rollback(state, run2)
        assert "新生成正文" in (vault / "n.md").read_text(encoding="utf-8")
        assert "v2" not in (vault / "n.md").read_text(encoding="utf-8")
        # 回滚 run1:首次创建的文件被移除
        commit.cmd_rollback(state, run1)
        assert not (vault / "n.md").exists()

    def test_rollback_unknown_run_exits(self, state):
        import pytest
        with pytest.raises(SystemExit):
            commit.cmd_rollback(state, "run_nonexistent")

    def test_commit_empty_staging_exits(self, state):
        import pytest
        with pytest.raises(SystemExit):
            commit.cmd_commit(state)


class TestQaCheck:
    def _seed(self, state):
        write_staged(state, "A.md", '---\ntitle: A\n---\n\n<!-- lkb-managed:start -->\n# A\n[[B]]\n<!-- lkb-managed:end -->\n')
        write_staged(state, "B.md", '---\ntitle: B\n---\n\n<!-- lkb-managed:start -->\n# B\n<!-- lkb-managed:end -->\n')

    def test_clean_pass(self, state):
        self._seed(state)
        issues, n_notes, n_items = qa_check.check(state)
        assert issues == []
        assert n_notes == 2

    def test_dangling_wikilink(self, state):
        write_staged(state, "A.md", '---\n---\n\n<!-- lkb-managed:start -->\n# A\n[[不存在]]\n<!-- lkb-managed:end -->\n')
        issues, _, _ = qa_check.check(state)
        assert any("wikilink" in i for i in issues)

    def test_dangling_asset(self, state):
        write_staged(state, "A.md", '---\n---\n\n<!-- lkb-managed:start -->\n![x](assets/missing.png)\n<!-- lkb-managed:end -->\n')
        issues, _, _ = qa_check.check(state)
        assert any("资产" in i for i in issues)

    def test_duplicate_basenames(self, state):
        write_staged(state, "a/b.md", "x")
        write_staged(state, "c/b.md", "x")
        issues, _, _ = qa_check.check(state)
        assert any("重名" in i for i in issues)

    def test_http_assets_ignored(self, state):
        write_staged(state, "A.md", '---\n---\n\n<!-- lkb-managed:start -->\n![x](https://example.com/i.png)\n<!-- lkb-managed:end -->\n')
        issues, _, _ = qa_check.check(state)
        assert issues == []

    def test_knowledge_sources_validated(self, state):
        common = __import__("common")
        common.write_json(Path(state) / "ir" / "knowledge.json", {
            "version": 1,
            "items": [{"id": "k_a", "type": "concept", "title": "a",
                       "sources": [{"src_id": "src_9999"}], "status": "accepted"}],
        })
        issues, _, _ = qa_check.check(state)
        assert any("src_9999" in i for i in issues)

"""文档转换器:pdf2md / docx2md / pptx2md / epub2md + 批处理容错。"""
import subprocess
import sys
from pathlib import Path

import docx2md
import epub2md
import pdf2md
import pptx2md
from conftest import (SCRIPTS, get_source, load_sources, make_docx, make_epub,
                      make_pdf, make_pptx)


def read_extracted(state, src_id):
    src = get_source(state, src_id)
    return open(f"{state}/{src['extracted_file']}", encoding="utf-8").read()


class TestPdf:
    def test_text_and_page_markers(self, state, materials):
        p = make_pdf(materials / "doc.pdf",
                     [("第一章 协程", "协程是可暂停恢复的函数。"),
                      ("第二章 await", "await 挂起当前协程。")])
        pdf2md.convert_one(state, p)
        md = read_extracted(state, "src_0001")
        assert "<!-- page:1 -->" in md and "<!-- page:2 -->" in md
        assert "协程" in md and "await" in md
        assert get_source(state, "src_0001")["meta"]["pages"] == 2

    def test_image_extraction(self, state, materials):
        p = make_pdf(materials / "doc.pdf",
                     [("图片页", "正文带图。")], image_every=1)
        pdf2md.convert_one(state, p)
        md = read_extracted(state, "src_0001")
        assert "![image 1](" in md
        assets = list((Path(state) / "assets" / "src_0001").glob("*.png"))
        assert len(assets) == 1
        assert get_source(state, "src_0001")["meta"]["images"] == 1

    def test_duplicate_skipped(self, state, materials):
        p = make_pdf(materials / "doc.pdf", [("A", "内容")])
        pdf2md.convert_one(state, p)
        pdf2md.convert_one(state, p)
        assert len(load_sources(state)) == 1


class TestDocx:
    def test_structure(self, state, materials):
        p = make_docx(materials / "doc.docx", heading="标题一", body="正文段落",
                      table=[["列A", "列B"], ["1", "2"]])
        docx2md.convert_one(state, p)
        md = read_extracted(state, "src_0001")
        assert "# 标题一" in md and md.index("# 标题一") < md.index("正文段落")
        assert "| 列A | 列B |" in md

    def test_image(self, state, materials):
        p = make_docx(materials / "doc.docx", body="有图", image=True)
        docx2md.convert_one(state, p)
        md = read_extracted(state, "src_0001")
        assert "![image 1](" in md
        assert len(list((Path(state) / "assets" / "src_0001").glob("*"))) == 1


class TestPptx:
    def test_slides_and_notes(self, state, materials):
        p = make_pptx(materials / "s.pptx",
                      [("第一页", "要点A"), ("第二页", "要点B")],
                      notes=["备注一", "备注二"])
        pptx2md.convert_one(state, p)
        md = read_extracted(state, "src_0001")
        assert "<!-- slide:1 -->" in md and "<!-- slide:2 -->" in md
        assert "要点A" in md and "要点B" in md
        assert "> 备注: 备注一" in md and "> 备注: 备注二" in md

    def test_slide_count_meta(self, state, materials):
        p = make_pptx(materials / "s.pptx", [("A", "B"), ("C", "D")])
        pptx2md.convert_one(state, p)
        assert get_source(state, "src_0001")["meta"]["slides"] == 2


class TestEpub:
    def test_chapters_and_image(self, state, materials):
        p = make_epub(materials / "b.epub",
                      [("第一章", "内容一"), ("第二章", "内容二")], image=True)
        epub2md.convert_one(state, p)
        md = read_extracted(state, "src_0001")
        assert "# 第一章" in md and "# 第二章" in md
        assert "![test image](" in md
        assert len(list((Path(state) / "assets" / "src_0001").glob("*.png"))) == 1


class TestBatchResilience:
    def _run_pdf_batch(self, state, files):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "pdf2md.py"), "--state", state,
             "--input", *[str(f) for f in files]],
            capture_output=True, text=True, encoding="utf-8", timeout=120)

    def test_corrupt_file_does_not_block_batch(self, state, materials):
        good = make_pdf(materials / "good.pdf", [("好文件", "正常内容")])
        bad = materials / "bad.pdf"
        bad.write_bytes(b"not a real pdf at all" * 10)
        r = self._run_pdf_batch(state, [bad, good])
        assert r.returncode == 1          # 有失败
        assert "[失败]" in r.stdout
        assert "1/2" in r.stdout
        sources = load_sources(state)
        assert len(sources) == 1          # 好文件仍入库
        assert sources[0]["title"] == "good"

    def test_missing_file_reported(self, state, materials):
        missing = materials / "nope.pdf"
        r = self._run_pdf_batch(state, [missing])
        assert r.returncode == 1
        assert "1/1" in r.stdout
        assert load_sources(state) == []

    def test_empty_and_truncated_docx(self, state, materials):
        bad = materials / "bad.docx"
        bad.write_bytes(b"PK\x03\x04truncated")
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "docx2md.py"), "--state", state,
             "--input", str(bad)],
            capture_output=True, text=True, encoding="utf-8", timeout=120)
        assert r.returncode == 1
        assert load_sources(state) == []

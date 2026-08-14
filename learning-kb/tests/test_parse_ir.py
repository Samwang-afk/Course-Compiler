"""parse_ir.py:markdown -> Document IR 的块切分。"""
import parse_ir


def parse(text):
    return parse_ir.parse_md(text)


class TestBlockTypes:
    def test_headings_with_levels(self):
        blocks = parse("# H1\n\n## H2\n\n### H3")
        assert [(b["type"], b.get("level"), b["text"]) for b in blocks] == [
            ("heading", 1, "H1"), ("heading", 2, "H2"), ("heading", 3, "H3")]

    def test_paragraph_continuation_lines(self):
        blocks = parse("第一行\n第二行\n第三行\n\n新段落")
        assert blocks[0]["type"] == "paragraph"
        assert blocks[0]["text"] == "第一行\n第二行\n第三行"
        assert blocks[1]["text"] == "新段落"

    def test_list_bullet_and_numbered(self):
        blocks = parse("- a\n- b\n- c\n\n1. 一\n2. 二")
        assert blocks[0]["type"] == "list"
        assert blocks[0]["text"].splitlines() == ["a", "b", "c"]
        assert blocks[1]["type"] == "list"
        assert blocks[1]["text"].splitlines() == ["一", "二"]

    def test_code_fence(self):
        blocks = parse("```python\nprint(1)\nprint(2)\n```")
        assert blocks[0]["type"] == "code"
        assert blocks[0]["text"] == "print(1)\nprint(2)"

    def test_quote(self):
        blocks = parse("> 引文一\n> 引文二")
        assert blocks[0]["type"] == "quote"
        assert blocks[0]["text"] == "引文一\n引文二"

    def test_table(self):
        md = "| 名称 | 值 |\n| --- | --- |\n| a | 1 |\n| b | 2 |"
        blocks = parse(md)
        assert blocks[0]["type"] == "table"
        assert "名称" in blocks[0]["text"]

    def test_image_block(self):
        blocks = parse("![图1](assets/src_0001/0001.png) <!-- page:2 -->")
        assert blocks[0]["type"] == "figure"
        assert blocks[0]["asset"] == "assets/src_0001/0001.png"
        assert blocks[0]["caption"] == "图1"
        assert blocks[0]["ref"] == "page:2"

    def test_equation(self):
        blocks = parse("$$F = ma$$")
        assert blocks[0]["type"] == "equation"
        assert blocks[0]["text"] == "F = ma"

    def test_inline_math_line(self):
        blocks = parse("$a^2 + b^2 = c^2$")
        assert blocks[0]["type"] == "equation"


class TestRefs:
    def test_page_ref_carries_forward(self):
        blocks = parse("<!-- page:3 -->\n\n正文一\n\n正文二")
        assert blocks[0]["ref"] == "page:3"
        assert blocks[1]["ref"] == "page:3"

    def test_ref_switches(self):
        blocks = parse("<!-- page:1 -->\n\nA\n\n<!-- page:2 -->\n\nB")
        assert blocks[0]["ref"] == "page:1"
        assert blocks[1]["ref"] == "page:2"

    def test_slide_and_time_refs(self):
        blocks = parse("<!-- slide:4 -->\n\nA\n\n<!-- time:12:34 -->\n\nB")
        assert blocks[0]["ref"] == "slide:4"
        assert blocks[1]["ref"] == "time:12:34"

    def test_src_comment_skipped(self):
        blocks = parse("<!-- src:src_0001 title:标题 -->\n\n正文")
        assert [b["type"] for b in blocks] == ["paragraph"]


class TestBlockIds:
    def test_sequential_unique_ids(self):
        blocks = parse("# A\n\n# B\n\n# C")
        assert [b["id"] for b in blocks] == ["b1", "b2", "b3"]
        assert [b["order"] for b in blocks] == [1, 2, 3]

    def test_empty_input(self):
        assert parse("") == []
        assert parse("\n\n\n") == []

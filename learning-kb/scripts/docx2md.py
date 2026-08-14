"""DOCX -> markdown(+图片资产)。用法:
  run.ps1 docx2md.py --state <dir> --input a.docx [b.docx ...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common


def convert_one(state_dir, path: Path):
    entry, dup = common.register(state_dir, "docx", path)
    if dup:
        print(f"[跳过] 内容重复,已有 {entry['id']} ({entry['title']})")
        return
    try:
        _convert(state_dir, path, entry)
    except Exception:
        common.remove_source(state_dir, entry["id"])
        raise


def _convert(state_dir, path: Path, entry):
    docx = common.need("docx", "python-docx")
    state, _, _ = common.load_state(state_dir)
    d = docx.Document(str(path))
    asset_dir = state / "assets" / entry["id"]
    asset_dir.mkdir(parents=True, exist_ok=True)
    rels = d.part.rels
    out = [f"<!-- src:{entry['id']} title:{entry['title']} -->", ""]
    img_n = 0

    def iter_blocks(parent):
        for child in parent.element.body.iterchildren():
            yield child

    for child in iter_blocks(d):
        tag = child.tag.split("}")[-1]
        if tag == "p":
            para = docx.text.paragraph.Paragraph(child, d)
            style = para.style.name or ""
            text = para.text.strip()
            embeds = []
            for run in para.runs:
                if run._element.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip"):
                    for r_id in [b.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                                 for b in run._element.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")]:
                        if r_id and r_id in rels:
                            part = rels[r_id].target_part
                            img_n += 1
                            name = f"{img_n:04d}.png"
                            (asset_dir / name).write_bytes(part.blob)
                            embeds.append(f"![image {img_n}](assets/{entry['id']}/{name})")
            if not text and not embeds:
                continue
            if style.startswith("Heading"):
                level = min(int(style.split()[-1]), 6)
                out.append("#" * level + " " + text)
            elif style == "List Bullet" or style == "List Paragraph":
                out.append("- " + text)
            elif style == "List Number":
                out.append("1. " + text)
            else:
                out.append(text)
            out.extend(embeds)
        elif tag == "tbl":
            table = docx.table.Table(child, d)
            for i, row in enumerate(table.rows):
                cells = [c.text.strip().replace("|", "\\|").replace("\n", " ") for c in row.cells]
                out.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    out.append("|" + "---|" * len(cells))
        out.append("")
    md = state / "extracted" / f"{entry['id']}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("\n".join(out), encoding="utf-8")
    common.update_source(state_dir, entry["id"],
                         extracted_file=f"extracted/{entry['id']}.md",
                         meta={"images": img_n}, status="extracted")
    print(f"[ok] {entry['id']} {path.name}: {img_n} 图")


def main():
    p = common.base_argparser("DOCX -> markdown")
    p.add_argument("--input", required=True, action="append", nargs="+", help="DOCX 文件,可多个")
    args = p.parse_args()
    sys.exit(common.run_batch(common.flatten(args.input),
                              lambda f: convert_one(args.state, Path(f))))


if __name__ == "__main__":
    main()

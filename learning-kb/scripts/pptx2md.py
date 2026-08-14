"""PPTX -> markdown(正文+备注+图片资产)。用法:
  run.ps1 pptx2md.py --state <dir> --input a.pptx [b.pptx ...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common


def shape_text(shape, out, asset_dir, entry, img_n):
    if shape.has_text_frame:
        for para in shape.text_frame.paragraphs:
            t = "".join(r.text for r in para.runs).strip()
            if t:
                lvl = para.level
                if shape.shape_type is not None and "PLACEHOLDER" in str(shape.shape_type):
                    out.append(t)
                else:
                    out.append(("  " * lvl) + "- " + t)
    if shape.shape_type == 19:  # table
        for i, row in enumerate(shape.table.rows):
            cells = [c.text.strip().replace("|", "\\|").replace("\n", " ") for c in row.cells]
            out.append("| " + " | ".join(cells) + " |")
            if i == 0:
                out.append("|" + "---|" * len(cells))
    if shape.shape_type == 13:  # picture
        try:
            blob = shape.image.blob
            ext = shape.image.ext or "png"
            img_n[0] += 1
            name = f"{img_n[0]:04d}.{ext}"
            (asset_dir / name).write_bytes(blob)
            out.append(f"![image {img_n[0]}](assets/{entry['id']}/{name})")
        except Exception:
            pass


def convert_one(state_dir, path: Path):
    entry, dup = common.register(state_dir, "pptx", path)
    if dup:
        print(f"[跳过] 内容重复,已有 {entry['id']} ({entry['title']})")
        return
    try:
        _convert(state_dir, path, entry)
    except Exception:
        common.remove_source(state_dir, entry["id"])
        raise


def _convert(state_dir, path: Path, entry):
    pptx = common.need("pptx", "python-pptx")
    state, _, _ = common.load_state(state_dir)
    prs = pptx.Presentation(str(path))
    asset_dir = state / "assets" / entry["id"]
    asset_dir.mkdir(parents=True, exist_ok=True)
    out = [f"<!-- src:{entry['id']} title:{entry['title']} -->", ""]
    img_n = [0]
    for sno, slide in enumerate(prs.slides, 1):
        out.append(f"<!-- slide:{sno} -->")
        for shape in sorted(slide.shapes, key=lambda s: (s.top is None, s.top or 0)):
            shape_text(shape, out, asset_dir, entry, img_n)
        if slide.has_notes_slide:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                out.append(f"> 备注: {notes}")
        out.append("")
    md = state / "extracted" / f"{entry['id']}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("\n".join(out), encoding="utf-8")
    common.update_source(state_dir, entry["id"],
                         extracted_file=f"extracted/{entry['id']}.md",
                         meta={"slides": len(prs.slides._sldIdLst), "images": img_n[0]},
                         status="extracted")
    print(f"[ok] {entry['id']} {path.name}: {len(prs.slides._sldIdLst)} 页, {img_n[0]} 图")


def main():
    p = common.base_argparser("PPTX -> markdown")
    p.add_argument("--input", required=True, action="append", nargs="+", help="PPTX 文件,可多个")
    args = p.parse_args()
    sys.exit(common.run_batch(common.flatten(args.input),
                              lambda f: convert_one(args.state, Path(f))))


if __name__ == "__main__":
    main()

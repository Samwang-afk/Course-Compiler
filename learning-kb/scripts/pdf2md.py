"""PDF -> markdown(+图片资产)。用法:
  run.ps1 pdf2md.py --state <dir> --input a.pdf [b.pdf ...]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common


def convert_one(state_dir, path: Path):
    entry, dup = common.register(state_dir, "pdf", path)
    if dup:
        print(f"[跳过] 内容重复,已有 {entry['id']} ({entry['title']})")
        return
    try:
        _convert(state_dir, path, entry)
    except Exception:
        common.remove_source(state_dir, entry["id"])
        raise


def _convert(state_dir, path: Path, entry):
    try:
        import pymupdf as fitz
    except ImportError:
        fitz = common.need("fitz", "pymupdf")
    state, _, _ = common.load_state(state_dir)
    doc = fitz.open(str(path))
    asset_dir = state / "assets" / entry["id"]
    asset_dir.mkdir(parents=True, exist_ok=True)
    out = [f"<!-- src:{entry['id']} title:{entry['title']} -->", ""]
    img_n = 0
    for pno, page in enumerate(doc, 1):
        out.append(f"<!-- page:{pno} -->")
        text = page.get_text("text").strip()
        if text:
            out.append(text)
        for xref, *_ in page.get_images(full=True):
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n - pix.alpha >= 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                img_n += 1
                name = f"{img_n:04d}.png"
                pix.save(str(asset_dir / name))
                rel = f"assets/{entry['id']}/{name}"
                out.append(f"![image {img_n}]({rel}) <!-- page:{pno} -->")
                pix = None
            except Exception:
                continue
        out.append("")
    md = state / "extracted" / f"{entry['id']}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("\n".join(out), encoding="utf-8")
    common.update_source(state_dir, entry["id"],
                         extracted_file=f"extracted/{entry['id']}.md",
                         meta={"pages": doc.page_count, "images": img_n},
                         status="extracted")
    print(f"[ok] {entry['id']} {path.name}: {doc.page_count} 页, {img_n} 图")


def main():
    p = common.base_argparser("PDF -> markdown")
    p.add_argument("--input", required=True, action="append", nargs="+", help="PDF 文件,可多个")
    args = p.parse_args()
    sys.exit(common.run_batch(common.flatten(args.input),
                              lambda f: convert_one(args.state, Path(f))))


if __name__ == "__main__":
    main()

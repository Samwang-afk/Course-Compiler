"""EPUB -> markdown(按章,含图片资产)。用法:
  run.ps1 epub2md.py --state <dir> --input a.epub [b.epub ...]
"""
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common

try:
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
except ImportError:
    pass


def xhtml_to_md(soup, asset_dir, entry, img_n, rel_base):
    out = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "img", "table", "pre", "blockquote"]):
        name = tag.name
        text = tag.get_text(" ", strip=True)
        if name.startswith("h"):
            out.append("#" * int(name[1]) + " " + text)
        elif name == "p":
            out.append(text)
        elif name == "li":
            out.append("- " + text)
        elif name == "blockquote":
            out.append("> " + text)
        elif name == "pre":
            out.append("```\n" + text + "\n```")
        elif name == "img":
            src = tag.get("src", "")
            try:
                blob = rel_base.get(src) or rel_base.get(Path(src).name)
                if blob:
                    img_n[0] += 1
                    ext = Path(src).suffix.lstrip(".").lower() or "png"
                    fname = f"{img_n[0]:04d}.{ext}"
                    (asset_dir / fname).write_bytes(blob)
                    alt = tag.get("alt") or f"image {img_n[0]}"
                    out.append(f"![{alt}](assets/{entry['id']}/{fname})")
            except Exception:
                continue
        elif name == "table":
            rows = []
            for tr in tag.find_all("tr"):
                cells = [c.get_text(" ", strip=True).replace("|", "\\|") for c in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            for i, cells in enumerate(rows):
                out.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    out.append("|" + "---|" * len(cells))
    return out


def convert_one(state_dir, path: Path):
    entry, dup = common.register(state_dir, "epub", path)
    if dup:
        print(f"[跳过] 内容重复,已有 {entry['id']} ({entry['title']})")
        return
    try:
        _convert(state_dir, path, entry)
    except Exception:
        common.remove_source(state_dir, entry["id"])
        raise


def _convert(state_dir, path: Path, entry):
    ebooklib = common.need("ebooklib", "ebooklib")
    bs4 = common.need("bs4", "beautifulsoup4")
    state, _, _ = common.load_state(state_dir)
    book = ebooklib.epub.read_epub(str(path))
    asset_dir = state / "assets" / entry["id"]
    asset_dir.mkdir(parents=True, exist_ok=True)
    rel_base = {}
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        rel_base[item.get_name()] = item.get_content()
        rel_base[Path(item.get_name()).name] = item.get_content()
    out = [f"<!-- src:{entry['id']} title:{entry['title']} -->", ""]
    img_n = [0]
    title = entry["title"]
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content()
        try:
            soup = bs4.BeautifulSoup(content, "xml")
        except Exception:
            soup = bs4.BeautifulSoup(content, "lxml")
        if not soup.find(["h1", "h2", "p"]):
            continue
        out.append("<!-- chapter -->")
        out.extend(xhtml_to_md(soup, asset_dir, entry, img_n, rel_base))
        out.append("")
    md = state / "extracted" / f"{entry['id']}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("\n".join(out), encoding="utf-8")
    common.update_source(state_dir, entry["id"],
                         extracted_file=f"extracted/{entry['id']}.md",
                         meta={"images": img_n[0]}, status="extracted")
    print(f"[ok] {entry['id']} {path.name}: {img_n[0]} 图")


def main():
    p = common.base_argparser("EPUB -> markdown")
    p.add_argument("--input", required=True, action="append", nargs="+", help="EPUB 文件,可多个")
    args = p.parse_args()
    sys.exit(common.run_batch(common.flatten(args.input),
                              lambda f: convert_one(args.state, Path(f))))


if __name__ == "__main__":
    main()

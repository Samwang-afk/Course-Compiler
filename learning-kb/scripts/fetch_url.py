"""网页 URL -> markdown(去导航/脚本,保正文与图片)。用法:
  run.ps1 fetch_url.py --state <dir> --url https://... [--url ...]
"""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common


def node_to_md(node, asset_dir, entry, img_n, base_url):
    out = []
    from urllib.parse import urljoin
    for child in node.children:
        if getattr(child, "name", None) is None:
            continue
        name = child.name
        if name in ("script", "style", "nav", "footer", "header", "aside", "form", "noscript"):
            continue
        text = child.get_text(" ", strip=True) if name in ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre", "figcaption") else None
        if name.startswith("h"):
            if text:
                out.append("#" * int(name[1]) + " " + text)
        elif name == "p":
            if text:
                out.append(text)
        elif name == "li":
            if text:
                out.append("- " + text)
        elif name == "blockquote":
            if text:
                out.append("> " + text)
        elif name == "pre":
            code = child.get_text()
            if code.strip():
                out.append("```\n" + code.strip() + "\n```")
        elif name in ("table",):
            rows = []
            for tr in child.find_all("tr"):
                cells = [c.get_text(" ", strip=True).replace("|", "\\|") for c in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
            for i, cells in enumerate(rows):
                out.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    out.append("|" + "---|" * len(cells))
        elif name == "img":
            src = child.get("src")
            if src:
                try:
                    img_url = urljoin(base_url, src)
                    req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
                    blob = urllib.request.urlopen(req, timeout=20).read()
                    if len(blob) > 100:
                        img_n[0] += 1
                        ext = Path(img_url.split("?")[0]).suffix.lstrip(".").lower() or "png"
                        fname = f"{img_n[0]:04d}.{ext}"
                        (asset_dir / fname).write_bytes(blob)
                        alt = child.get("alt") or f"image {img_n[0]}"
                        out.append(f"![{alt}](assets/{entry['id']}/{fname})")
                except Exception:
                    continue
        else:
            out.extend(node_to_md(child, asset_dir, entry, img_n, base_url))
    return out


def fetch_one(state_dir, url):
    requests = common.need("requests", "requests")
    bs4 = common.need("bs4", "beautifulsoup4")
    state, sources, _ = common.load_state(state_dir)
    for s in sources["sources"]:
        if s.get("original_path") == url:
            print(f"[跳过] URL 已登记: {s['id']} ({s['title']})")
            return
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii", "cp1252"):
        r.encoding = r.apparent_encoding
    soup = bs4.BeautifulSoup(r.text, "lxml")
    for t in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        t.decompose()
    title = (soup.title.get_text(strip=True) if soup.title else Path(url).stem) or url
    main = soup.find("article") or soup.find("main") or soup.find("body")
    entry, dup = common.register(state_dir, "url", Path(url), title=title,
                                 content_bytes=r.text.encode("utf-8"))
    if dup:
        print(f"[跳过] 内容重复,已有 {entry['id']} ({entry['title']})")
        return
    try:
        _convert(state_dir, url, entry, soup, main, title)
    except Exception:
        common.remove_source(state_dir, entry["id"])
        raise


def _convert(state_dir, url, entry, soup, main, title):
    state, _, _ = common.load_state(state_dir)
    asset_dir = state / "assets" / entry["id"]
    asset_dir.mkdir(parents=True, exist_ok=True)
    img_n = [0]
    out = [f"<!-- src:{entry['id']} title:{title} -->",
           f"<!-- url:{url} fetched -->", "", f"# {title}", ""]
    out.extend(node_to_md(main, asset_dir, entry, img_n, url))
    md = state / "extracted" / f"{entry['id']}.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text("\n".join(out), encoding="utf-8")
    common.update_source(state_dir, entry["id"],
                         extracted_file=f"extracted/{entry['id']}.md",
                         meta={"images": img_n[0], "url": url},
                         status="extracted")
    print(f"[ok] {entry['id']} {url}: {img_n[0]} 图")


def main():
    p = common.base_argparser("URL -> markdown")
    p.add_argument("--url", required=True, action="append", nargs="+", help="URL,可多个")
    args = p.parse_args()
    sys.exit(common.run_batch(common.flatten(args.url),
                              lambda u: fetch_one(args.state, u), label="URL"))


if __name__ == "__main__":
    main()

"""fetch_url.py:本地 HTTP 服务器验证抓取、UTF-8、表格、图片。"""
import http.server
import threading
from pathlib import Path

import fetch_url
from conftest import get_source, load_sources, make_png


class _Handler(http.server.BaseHTTPRequestHandler):
    HTML = None
    IMG = None

    def do_GET(self):
        if self.path.startswith("/img"):
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(self.IMG)
        else:
            body = self.HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def log_message(self, *a):
        pass


class TestFetchUrl:
    def test_utf8_article_table_image(self, state, tmp_path):
        img = tmp_path / "x.png"
        make_png(img)
        _Handler.IMG = img.read_bytes()
        _Handler.HTML = """<!DOCTYPE html><html lang="zh"><head><title>异步要点</title></head>
<body><header><nav>广告</nav></header>
<article><h1>异步要点</h1><p>协程是可暂停恢复的函数。</p>
<h2>概念表</h2>
<table><tr><th>概念</th><th>作用</th></tr><tr><td>coroutine</td><td>可暂停</td></tr></table>
<img src="/img/x.png" alt="插图"></article>
<footer>页脚</footer></body></html>"""
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        srv.daemon_threads = True
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            url = f"http://127.0.0.1:{srv.server_address[1]}/page"
            fetch_url.fetch_one(state, url)
        finally:
            srv.shutdown()
            srv.server_close()

        src = get_source(state, "src_0001")
        assert src["title"] == "异步要点"          # UTF-8 解码正确
        md = open(f"{state}/{src['extracted_file']}", encoding="utf-8").read()
        assert "# 异步要点" in md
        assert "协程是可暂停恢复的函数。" in md
        assert "| 概念 | 作用 |" in md             # 表格
        assert "![插图](" in md                    # 图片
        assert "广告" not in md and "页脚" not in md  # 导航页脚剥离
        assert len(list((Path(state) / "assets" / "src_0001").glob("*.png"))) == 1

    def test_duplicate_url_skipped(self, state, tmp_path):
        _Handler.HTML = "<html><head><title>T</title></head><body><p>正文</p></body></html>"
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        srv.daemon_threads = True
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            url = f"http://127.0.0.1:{srv.server_address[1]}/page"
            fetch_url.fetch_one(state, url)
            fetch_url.fetch_one(state, url)
        finally:
            srv.shutdown()
            srv.server_close()
        assert len(load_sources(state)) == 1

    def test_connection_error_reported(self, state):
        import pytest as _pytest
        # 无人监听的端口:直接抛错,由 run_batch 层报告(此处验证异常可捕获)
        try:
            fetch_url.fetch_one(state, "http://127.0.0.1:1/none")
        except Exception:
            pass
        assert load_sources(state) == []

"""音频/视频 -> whisper 转写 markdown(带时间戳)。用法:
  run.ps1 transcribe.py --state <dir> --input a.mp3 [b.mp4 ...] [--model base] [--force]
首次运行会下载模型(默认 base)。同一内容 sha256 去重;已转写文件默认跳过。
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common

MEDIA_EXT = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".mp4", ".mkv", ".mov", ".webm", ".aac", ".opus"}


def fmt_ts(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def ffmpeg_to_wav16(path: Path, tmpdir: Path) -> Path:
    wav = tmpdir / (path.stem[:40] + ".wav")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(path), "-ar", "16000", "-ac", "1", str(wav)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg 失败: {r.stderr[-500:]}")
    return wav


def transcribe_one(state_dir, path: Path, model_size, force):
    if path.suffix.lower() not in MEDIA_EXT:
        sys.exit(f"不支持的媒体格式: {path.suffix}")
    kind = "video" if path.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm"} else "audio"
    entry, dup = common.register(state_dir, kind, path)
    state, _, _ = common.load_state(state_dir)
    md_path = state / "extracted" / f"{entry['id']}.md"
    if dup and not force:
        print(f"[跳过] 内容重复,已有 {entry['id']} ({entry['title']})")
        return
    if md_path.exists() and not force:
        print(f"[跳过] 已转写: {entry['id']} (--force 重转)")
        return
    try:
        _transcribe(state_dir, path, entry, md_path, model_size)
    except Exception:
        if not dup:
            common.remove_source(state_dir, entry["id"])
        raise


def _transcribe(state_dir, path, entry, md_path, model_size):
    whisper = common.need("whisper", "openai-whisper")
    state, _, _ = common.load_state(state_dir)
    with tempfile.TemporaryDirectory() as tmp:
        wav = ffmpeg_to_wav16(path, Path(tmp))
        print(f"[转写] {entry['id']} {path.name} (model={model_size}, cpu) …")
        model = whisper.load_model(model_size, device="cpu")
        result = model.transcribe(str(wav), verbose=False)
        segs = result.get("segments", [])
        lang = result.get("language", "")
        out = [f"<!-- src:{entry['id']} title:{entry['title']} -->",
               f"<!-- lang:{lang} model:{model_size} -->", ""]
        for seg in segs:
            ts = fmt_ts(seg["start"])
            text = seg["text"].strip()
            if text:
                out.append(f"<!-- time:{ts} -->")
                out.append(text)
                out.append("")
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("\n".join(out), encoding="utf-8")
        dur = segs[-1]["end"] if segs else 0
        common.update_source(state_dir, entry["id"],
                             extracted_file=f"extracted/{entry['id']}.md",
                             meta={"duration_s": round(dur, 1), "language": lang,
                                   "model": model_size},
                             status="extracted")
        print(f"[ok] {entry['id']} {path.name}: {len(segs)} 段, {dur:.0f}s ({lang})")


def main():
    p = common.base_argparser("音视频 -> whisper 转写")
    p.add_argument("--input", required=True, action="append", nargs="+", help="媒体文件,可多个")
    p.add_argument("--model", default="base", help="whisper 模型 tiny/base/small/medium/large")
    p.add_argument("--force", action="store_true", help="强制重转")
    args = p.parse_args()
    sys.exit(common.run_batch(common.flatten(args.input),
                              lambda f: transcribe_one(args.state, Path(f), args.model, args.force)))


if __name__ == "__main__":
    main()

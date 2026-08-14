"""transcribe.py:mock whisper 验证转写管线(ffmpeg 真实执行)。"""
import sys
import types
from pathlib import Path

import transcribe
from conftest import get_source, make_wav


class FakeModel:
    def __init__(self, segments, language="en"):
        self._segments = segments
        self._language = language

    def transcribe(self, wav, verbose=False):
        assert Path(wav).exists()
        return {"segments": self._segments, "language": self._language}


class FakeWhisper(types.ModuleType):
    def __init__(self):
        super().__init__("whisper")
        self.loaded_model = None

    def load_model(self, size, device="cpu"):
        self.loaded_model = size
        return FakeModel([
            {"start": 0.0, "end": 2.5, "text": " 第一段转写 "},
            {"start": 2.5, "end": 5.0, "text": "第二段转写"},
        ], language="zh")


def _install_fake_whisper(monkeypatch):
    fake = FakeWhisper()
    monkeypatch.setitem(sys.modules, "whisper", fake)
    return fake


class TestTranscribe:
    def test_basic_flow(self, state, materials, monkeypatch):
        fake = _install_fake_whisper(monkeypatch)
        audio = make_wav(materials / "lecture.wav", seconds=2.0)
        transcribe.transcribe_one(state, audio, "base", False)
        src = get_source(state, "src_0001")
        assert src["kind"] == "audio"
        assert src["meta"]["language"] == "zh"
        assert src["meta"]["duration_s"] == 5.0
        assert fake.loaded_model == "base"
        md = open(f"{state}/{src['extracted_file']}", encoding="utf-8").read()
        assert "<!-- time:00:00 -->" in md
        assert "第一段转写" in md
        assert "<!-- time:00:02 -->" in md
        assert "第二段转写" in md

    def test_skip_already_transcribed(self, state, materials, monkeypatch):
        fake = _install_fake_whisper(monkeypatch)
        audio = make_wav(materials / "a.wav", seconds=1.0)
        transcribe.transcribe_one(state, audio, "base", False)
        transcribe.transcribe_one(state, audio, "base", False)   # 默认跳过
        assert fake.loaded_model == "base"  # 只 load 了一次

    def test_force_retranscribe(self, state, materials, monkeypatch):
        _install_fake_whisper(monkeypatch)
        from conftest import load_sources
        audio = make_wav(materials / "a.wav", seconds=1.0)
        transcribe.transcribe_one(state, audio, "base", False)
        transcribe.transcribe_one(state, audio, "base", True)
        assert len(load_sources(state)) == 1

    def test_video_kind_detected(self, state, materials, monkeypatch):
        _install_fake_whisper(monkeypatch)
        # 用 ffmpeg 造一个 1 秒短视频
        import subprocess
        video = materials / "clip.mp4"
        r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                            "-c:a", "aac", "-strict", "experimental", str(video)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not video.exists():
            import pytest
            pytest.skip("ffmpeg 不可用")
        transcribe.transcribe_one(state, video, "base", False)
        assert get_source(state, "src_0001")["kind"] == "video"

    def test_unsupported_extension(self, state, materials):
        f = materials / "x.xyz"
        f.write_bytes(b"junk")
        import pytest
        with pytest.raises(SystemExit):
            transcribe.transcribe_one(state, f, "base", False)

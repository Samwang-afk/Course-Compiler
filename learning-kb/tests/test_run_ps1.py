"""run.ps1 冒烟:经 PowerShell 入口跑 commit.py status(验证 venv 引导与参数透传)。"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import SCRIPTS

pytestmark = pytest.mark.powershell


@pytest.fixture
def venv_ready():
    venv_py = SCRIPTS.parent / ".venv" / "Scripts" / "python.exe"
    if not venv_py.exists():
        pytest.skip(".venv 未安装(先运行 scripts/setup.ps1)")
    return str(venv_py)


class TestRunPs1:
    def test_status_via_powershell(self, state_with_brief, venv_ready):
        if shutil.which("powershell") is None:
            pytest.skip("无 powershell")
        r = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(SCRIPTS / "run.ps1"),
             "commit.py", "--state", state_with_brief, "status"],
            capture_output=True, text=True, encoding="utf-8", timeout=180)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "stage" in r.stdout

    def test_missing_script_reports_error(self, state_with_brief, venv_ready):
        if shutil.which("powershell") is None:
            pytest.skip("无 powershell")
        r = subprocess.run(
            ["powershell", "-NoProfile", "-File", str(SCRIPTS / "run.ps1"),
             "definitely_not_a_script.py", "--state", state_with_brief],
            capture_output=True, text=True, encoding="utf-8", timeout=180)
        assert r.returncode != 0

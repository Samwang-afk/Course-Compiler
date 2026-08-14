"""staging -> vault 提交 / 回滚 / 状态。用法:
  run.ps1 commit.py --state <dir> status
  run.ps1 commit.py --state <dir> commit
  run.ps1 commit.py --state <dir> rollback <run_id>
  run.ps1 commit.py --state <dir> list-runs
"""
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common

MANAGED_RE = re.compile(r"(?s)<!-- lkb-managed:start -->.*?<!-- lkb-managed:end -->")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.S)


def merge_managed(new_text, old_text):
    """新生成内容与既有笔记拼接:managed 区域与 frontmatter 用新的,
    其余(用户手写)保留旧的。双方都有 managed 标记才合并,否则整体用新。"""
    nm = MANAGED_RE.search(new_text)
    om = MANAGED_RE.search(old_text)
    if not nm or not om:
        return new_text
    nfm = FRONTMATTER_RE.match(new_text)
    ofm = FRONTMATTER_RE.match(old_text)
    merged = MANAGED_RE.sub(nm.group(0), old_text, count=1)
    if nfm and ofm:
        merged = FRONTMATTER_RE.sub(nfm.group(0), merged, count=1)
    return merged


def vault_path(state):
    return state.parent


def cmd_status(state_dir):
    _, sources, status = common.load_state(state_dir)
    print(f"stage: {status.get('stage')}")
    for s in sources["sources"]:
        print(f"  {s['id']} [{s['kind']}] {s['status']} {s.get('title', '')[:40]}")


def cmd_commit(state_dir):
    state, sources, status = common.load_state(state_dir)
    staging = state / "staging"
    if not staging.exists() or not list(staging.rglob("*")):
        sys.exit("staging 为空,先 compile")
    run_id = "run_" + common.now().replace("-", "").replace(":", "").split("+")[0]
    n = 0
    base = run_id
    while (state / "runs" / f"{run_id}.json").exists():
        n += 1
        run_id = f"{base}_{n}"
    backup_dir = state / "runs" / "backups" / run_id
    backup_dir.mkdir(parents=True, exist_ok=True)
    vault = vault_path(state)
    actions = []
    staged_files = [p for p in sorted(staging.rglob("*")) if p.is_file()]
    for sp in staged_files:
        rel = sp.relative_to(staging)
        vp = vault / rel
        op = "create"
        if vp.exists():
            op = "update"
            bkp = backup_dir / rel
            bkp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(vp, bkp)
        vp.parent.mkdir(parents=True, exist_ok=True)
        if op == "update":
            new_text = sp.read_bytes().decode("utf-8")
            old_text = vp.read_bytes().decode("utf-8")
            vp.write_bytes(merge_managed(new_text, old_text).encode("utf-8"))
        else:
            shutil.copy2(sp, vp)
        actions.append({"stage": "commit", "files": [{"staged": rel.as_posix(),
                                                       "vault": rel.as_posix(), "op": op}]})
    manifest = {"run_id": run_id, "ts": common.now(),
                "backup_dir": f"runs/backups/{run_id}",
                "actions": actions}
    common.write_json(state / "runs" / f"{run_id}.json", manifest)
    for s in sources["sources"]:
        if s["status"] == "merged":
            s["status"] = "compiled"
    status["stage"] = "done"
    common.save_state(state_dir, sources, status)
    print(f"[ok] 已提交 {len(staged_files)} 个文件到 {vault}")
    print(f"     run_id={run_id}(回滚: run.ps1 commit.py --state {state_dir} rollback {run_id})")


def cmd_rollback(state_dir, run_id):
    state, sources, status = common.load_state(state_dir)
    mf = state / "runs" / f"{run_id}.json"
    if not mf.exists():
        sys.exit(f"无此 run: {run_id}")
    manifest = common.read_json(mf)
    vault = vault_path(state)
    backup_dir = state / manifest["backup_dir"]
    for action in manifest["actions"]:
        for f in action["files"]:
            vp = vault / f["vault"]
            bkp = backup_dir / f["vault"]
            if f["op"] == "create" and vp.exists():
                vp.unlink()
            elif f["op"] == "update":
                if bkp.exists():
                    shutil.copy2(bkp, vp)
                else:
                    print(f"警告: 缺备份 {bkp},保留现状 {vp}")
    print(f"[ok] 已回滚 {run_id}")


def cmd_list_runs(state_dir):
    state, _, _ = common.load_state(state_dir)
    for mf in sorted((state / "runs").glob("run_*.json")):
        print(mf.stem)


def main():
    p = common.base_argparser("commit/rollback/status")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("commit")
    rp = sub.add_parser("rollback")
    rp.add_argument("run_id")
    sub.add_parser("list-runs")
    args = p.parse_args()
    {"status": cmd_status, "commit": cmd_commit, "list-runs": cmd_list_runs}[args.cmd](args.state) \
        if args.cmd != "rollback" else cmd_rollback(args.state, args.run_id)


if __name__ == "__main__":
    main()

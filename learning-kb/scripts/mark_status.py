"""把来源状态推进到指定值。用法:
  run.ps1 mark_status.py --state <dir> --src src_0001 --status proposed [--stage extract]
可选 --stage 同时设置管线总阶段。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import common


def main():
    p = common.base_argparser("推进来源状态")
    p.add_argument("--src", required=True)
    p.add_argument("--status", required=True,
                   choices=["registered", "extracted", "parsed", "proposed", "merged", "compiled"])
    p.add_argument("--stage", help="同时设置管线总阶段")
    args = p.parse_args()
    common.update_source(args.state, args.src, status=args.status)
    if args.stage:
        _, sources, status = common.load_state(args.state)
        status["stage"] = args.stage
        common.save_state(args.state, sources, status)
    print(f"[ok] {args.src} -> {args.status}" + (f" (stage={args.stage})" if args.stage else ""))


if __name__ == "__main__":
    main()

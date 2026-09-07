"""Run from repository root: python -m scripts.player --help."""
import argparse
import json
import sys

from .protocol import ControlFailure, MODES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("windows", help="List visible Roblox Studio windows only")
    for name in ("capture", "record"):
        command = commands.add_parser(name)
        target = command.add_mutually_exclusive_group(required=True)
        target.add_argument("--hwnd", type=int)
        target.add_argument("--title-match")
        command.add_argument("--output", required=True)
        command.add_argument("--crop", nargs=4, type=int, metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"))
        command.add_argument("--mode", choices=sorted(MODES), required=True)
        command.add_argument("--build-id", required=True)
        command.add_argument("--session-id", required=True)
        command.add_argument("--studio-id", required=True)
        if name == "record":
            command.add_argument("--seconds", type=float, required=True)
            command.add_argument("--fps", type=float, default=8)
            command.add_argument("--ffmpeg")
    command = commands.add_parser("input", help="Execute one bounded action under explicit runtime lease")
    command.add_argument("--action", required=True)
    command.add_argument("--lease", required=True)
    command.add_argument("--result", required=True)
    command = commands.add_parser("_watchdog", help=argparse.SUPPRESS)
    command.add_argument("--lock", required=True)
    command.add_argument("--deadline", type=float, required=True)
    command.add_argument("--token", required=True)
    args = parser.parse_args()
    try:
        if args.command == "_watchdog":
            from .input import watchdog
            watchdog(args.lock, args.deadline, args.token)
            return 0
        if args.command == "windows":
            from .capture import list_windows
            result = [w for w in list_windows() if "roblox studio" in w["title"].casefold()]
        elif args.command == "input":
            from .input import execute
            result = execute(args.action, args.lease, args.result)
        else:
            from .capture import select_window, save_capture
            target = select_window(args.hwnd, args.title_match)
            context = {"mode": args.mode, "build_id": args.build_id,
                       "session_id": args.session_id, "studio_id": args.studio_id}
            if args.command == "capture":
                result = save_capture(target, args.output, args.crop, context)
            else:
                from .record import record_window
                result = record_window(target, args.output, args.seconds, args.fps, args.crop, context, args.ffmpeg)
                result = {key: value for key, value in result.items() if key != "frame_ledger"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) and result.get("status") == "CONTROL_FAILURE" else 0
    except (ControlFailure, OSError, ValueError) as exc:
        print(json.dumps({"status": "CONTROL_FAILURE", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

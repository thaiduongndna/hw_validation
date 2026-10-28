import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from .scope import TekScope
from .service import acquire, save_run_log
from .workbook import load_spec, save_results


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Tektronix MSO6B → Excel (real SCPI socket, no simulator)")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("gui", help="Open the Windows GUI")
    for name in ("connect", "run"):
        command = commands.add_parser(name)
        command.add_argument("--host", required=True, help="Scope IP / hostname")
        command.add_argument("--port", type=int, default=4000)
        command.add_argument("--io-timeout", type=float, default=5)
        if name == "run":
            command.add_argument("--workbook", required=True)
            command.add_argument("--sheet")
            command.add_argument("--map", action="append", required=True, metavar="TEST_ID=MEAS1")
            command.add_argument("--single", action="store_true", help="Capture a new single acquisition; otherwise freeze current")
            command.add_argument("--acquisition-timeout", type=float, default=15)
            command.add_argument("--save", action="store_true", help="Fill results in the selected workbook, with backup")
            command.add_argument("--output", help="Save to a new XLSX path instead")
    args = parser.parse_args(argv)
    if args.command in (None, "gui"):
        from .gui import launch
        launch()
        return 0
    scope = None
    try:
        document, mapping = None, {}
        if args.command == "run":
            document = load_spec(args.workbook, args.sheet)
            for item in args.map:
                if "=" not in item:
                    raise ValueError("Use the mapping format TEST_ID=MEAS1.")
                tid, slot = item.split("=", 1)
                tid, slot = tid.strip(), slot.strip().upper()
                if tid in mapping:
                    raise ValueError("Test ID is assigned more than once: " + tid)
                mapping[tid] = slot
        scope = TekScope(args.host, args.port, args.io_timeout)
        scope.connect()
        if args.command == "connect":
            from dataclasses import asdict
            print(json.dumps({"identity": scope.identity, "measurements": [asdict(d) for d in scope.measurements()]}, ensure_ascii=False, indent=2))
            return 0
        run = acquire(document, mapping, scope, args.single, args.acquisition_timeout)
        save_run_log(run, scope, document.path.parent)
        saved = save_results(document, run.results, run.run_id, args.output) if args.save or args.output else None
        payload = run.as_dict()
        payload["saved_workbook"] = str(saved) if saved else None
        payload["counts"] = dict(Counter(r.status for r in run.results))
        print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
        if any(r.status == "FAIL" for r in run.results):
            return 1
        return 0 if all(r.status == "PASS" for r in run.results) else 3
    except Exception as exc:
        print(json.dumps({"error": str(exc), "type": type(exc).__name__}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        if scope:
            scope.close()

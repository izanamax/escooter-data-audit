"""CLI with explicit success, validation-failure and input-error exit codes."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

from . import __version__, audit_splits


def _reject_constant(value):
    raise ValueError(f"Non-standard JSON numeric constant: {value}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit COCO boxes and split leakage without changing inputs.")
    parser.add_argument("--split", action="append", required=True, metavar="NAME=FILE")
    parser.add_argument("--output", type=Path, help="Write JSON report; otherwise print to stdout.")
    parser.add_argument("--require-sequences", action="store_true", help="Missing source_sequence becomes an error.")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    splits, inputs, paths = {}, {}, set()
    try:
        for spec in args.split:
            name, separator, filename = spec.partition("=")
            if not separator or not name.strip() or not filename:
                raise ValueError("Each --split must be NAME=FILE.")
            if name in splits:
                raise ValueError(f"Repeated split name: {name}")
            path = Path(filename)
            paths.add(path.resolve())
            payload = path.read_bytes()
            splits[name] = json.loads(payload.decode("utf-8-sig"), parse_constant=_reject_constant)
            inputs[name] = dict(file=path.name, sha256=hashlib.sha256(payload).hexdigest())
        if args.output and args.output.resolve() in paths:
            raise ValueError("The report path must not overwrite an input annotation file.")
        report = audit_splits(splits, require_sequences=args.require_sequences)
        report.update(tool_version=__version__, inputs=inputs)
        rendered = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
            print(f"{report['status'].upper()}: {report['error_count']} errors, {report['warning_count']} warnings; {args.output}")
        else:
            print(rendered, end="")
        return 1 if report["error_count"] else 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"Input/output error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

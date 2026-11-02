import argparse
import json
from pathlib import Path

from .batch import process
from .config import load_profiles
from .io import MAX_BYTES, read_upload, workbook_bytes


def main():
    parser = argparse.ArgumentParser(description="Local marketplace contribution calculator")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rules", type=Path)
    parser.add_argument("--mapping", type=Path, help="JSON original-column to canonical-field mapping")
    parser.add_argument("--locale", choices=["en", "fa", "comma"], default="en")
    parser.add_argument(
        "--applicable-costs",
        help="Comma-separated applicable cost fields; absent unlisted costs are explicitly inapplicable",
    )
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > MAX_BYTES:
            raise ValueError("FILE_TOO_LARGE")
        mapping = json.loads(args.mapping.read_text()) if args.mapping else None
        rows = read_upload(args.input.read_bytes(), args.input.name, mapping)
        result = process(
            rows,
            profiles=load_profiles(args.rules),
            locale=args.locale,
            applicable_costs=set(args.applicable_costs.split(","))
            if args.applicable_costs is not None
            else None,
        )
        args.output.write_bytes(workbook_bytes(result))
        print(json.dumps(result["Summary"], ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Cannot process input: {exc}\n")


if __name__ == "__main__":
    main()

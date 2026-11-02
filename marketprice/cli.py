import argparse
import json
from pathlib import Path

from .batch import process
from .config import load_profiles
from .flexible import calculate_catalog
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
    parser.add_argument(
        "--flexible", action="store_true", help="Use included costs only; preserve per-product blanks"
    )
    parser.add_argument("--currency", help="Required file default in flexible mode")
    parser.add_argument("--target-margin", help="Required objective in flexible mode, e.g. 10%%")
    args = parser.parse_args()
    try:
        if args.input.stat().st_size > MAX_BYTES:
            raise ValueError("FILE_TOO_LARGE")
        mapping = json.loads(args.mapping.read_text()) if args.mapping else None
        rows = read_upload(args.input.read_bytes(), args.input.name, mapping)
        if args.flexible and (not args.currency or not args.target_margin):
            raise ValueError("--flexible requires --currency and --target-margin")
        calculator = calculate_catalog if args.flexible else process
        mode_settings = (
            {"currency": args.currency, "target_margin": args.target_margin}
            if args.flexible
            else {
                "applicable_costs": set(args.applicable_costs.split(","))
                if args.applicable_costs is not None
                else None
            }
        )
        result = calculator(
            rows,
            profiles=load_profiles(args.rules),
            locale=args.locale,
            **mode_settings,
        )
        args.output.write_bytes(workbook_bytes(result))
        print(json.dumps(result["Summary"], ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Cannot process input: {exc}\n")


if __name__ == "__main__":
    main()

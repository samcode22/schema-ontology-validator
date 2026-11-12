"""Command-line interface for the ontology validator.

Supports:
  - Validating files and directories
  - Multiple output formats (text, JSON)
  - Exit codes for automation
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from .loader import Ontology
from .validator import validate_entity_file
from .violations import Violation


def _iter_yaml_files(paths: Iterable[Path]) -> Iterable[Path]:
    """Yield every YAML file under each path.

    Skips the ontology manifest itself and any nested tool directories.
    """
    seen: set[Path] = set()
    for p in paths:
        if not p.exists():
            print(f"warning: path does not exist: {p}", file=sys.stderr)
            continue

        if p.is_file():
            if p.suffix.lower() in (".yaml", ".yml"):
                if p.resolve() not in seen:
                    seen.add(p.resolve())
                    yield p
            continue

        # Recursively find YAML files
        for f in sorted(list(p.rglob("*.yaml")) + list(p.rglob("*.yml"))):
            rel_str = str(f).replace("\\", "/")

            # Skip the ontology file itself
            if "ontology.yaml" in rel_str:
                continue

            # Skip tool/test directories
            if "/tools/" in rel_str or "/.venv" in rel_str or "/__pycache__" in rel_str:
                continue

            if f.resolve() in seen:
                continue

            seen.add(f.resolve())
            yield f


def _format_text(violations: list[Violation]) -> str:
    """Format violations as human-readable text."""
    if not violations:
        return "✓ All valid"

    by_file: dict[str, list[Violation]] = defaultdict(list)
    for v in violations:
        by_file[v.file or "<unknown>"].append(v)

    lines: list[str] = []
    for fpath in sorted(by_file):
        lines.append(f"\n{fpath}")
        for v in sorted(by_file[fpath], key=lambda x: (x.entity_ref, x.code)):
            lines.append(f"  {v.format()}")

    return "\n".join(lines)


def _format_json(violations: list[Violation]) -> str:
    """Format violations as JSON."""
    data = [
        {
            "code": v.code,
            "severity": v.severity.value,
            "rule": v.rule,
            "entity_ref": v.entity_ref,
            "message": v.message,
            "file": v.file,
            "extra": v.extra if v.extra else None,
        }
        for v in violations
    ]
    return json.dumps(data, indent=2)


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point.

    Returns:
        0: No violations found
        1: Violations found
        2: Invalid invocation or error
    """
    parser = argparse.ArgumentParser(
        prog="ontology-validator",
        description="Validate YAML catalog entities against an ontology schema.",
    )

    # Global arguments
    parser.add_argument(
        "--ontology",
        type=Path,
        default=Path("ontology.yaml"),
        help="Path to ontology.yaml (default: ontology.yaml)",
    )

    # Subcommands
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ── validate subcommand ───────────────────────────────────────────────────
    p_validate = sub.add_parser(
        "validate",
        help="Validate files or directories of catalog YAML.",
    )
    p_validate.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to validate",
    )
    p_validate.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # ── list-rules subcommand ──────────────────────────────────────────────────
    p_list = sub.add_parser(
        "list-rules",
        help="List all violation codes and their meanings.",
    )

    # ── suggest subcommand ─────────────────────────────────────────────────────
    p_suggest = sub.add_parser(
        "suggest",
        help="Get AI-powered suggestions for violations using OpenAI API.",
    )
    p_suggest.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files to analyze for violations",
    )
    p_suggest.add_argument(
        "--api-key",
        default=None,
        help="OpenAI API key (uses OPENAI_API_KEY env var if not provided)",
    )

    # ── analyze subcommand ─────────────────────────────────────────────────────
    p_analyze = sub.add_parser(
        "analyze",
        help="Get AI recommendations for improving your schema.",
    )
    p_analyze.add_argument(
        "schema",
        type=Path,
        help="Schema file to analyze",
    )
    p_analyze.add_argument(
        "--api-key",
        default=None,
        help="OpenAI API key (uses OPENAI_API_KEY env var if not provided)",
    )

    args = parser.parse_args(argv)

    # Handle list-rules
    if args.cmd == "list-rules":
        from .violations import CODE_FAMILY

        for code in sorted(CODE_FAMILY.keys()):
            print(f"{code:8} {CODE_FAMILY[code]}")
        return 0

    # Handle suggest
    if args.cmd == "suggest":
        try:
            from .ai_suggestions import get_violation_suggestion
        except ImportError:
            print(
                "error: openai package not installed. "
                "Run: pip install openai",
                file=sys.stderr,
            )
            return 2

        # Load ontology
        if not args.ontology.exists():
            print(
                f"error: ontology file not found: {args.ontology}",
                file=sys.stderr,
            )
            return 2

        try:
            ontology = Ontology.from_file(args.ontology)
        except Exception as e:
            print(f"error: could not load ontology: {e}", file=sys.stderr)
            return 2

        # Validate files and collect violations
        yaml_files = list(_iter_yaml_files(args.paths))
        if not yaml_files:
            print("warning: no YAML files found", file=sys.stderr)
            return 0

        all_violations: list[Violation] = []
        for yaml_file in yaml_files:
            violations = validate_entity_file(yaml_file, ontology)
            all_violations.extend(violations)

        if not all_violations:
            print("✓ No violations found!")
            return 0

        # Get AI suggestions for each violation
        print("\n" + "="*70)
        print("AI-POWERED VIOLATION SUGGESTIONS")
        print("="*70)

        for v in all_violations[:5]:  # Limit to first 5 to avoid API quota
            print(f"\n📍 {v.entity_ref} - {v.code}")
            print(f"   Issue: {v.message}")
            print("   💡 AI Suggestion:")
            try:
                suggestion = get_violation_suggestion(v, api_key=args.api_key)
                for line in suggestion.split("\n"):
                    print(f"      {line}")
            except Exception as e:
                print(f"      Could not generate suggestion: {e}")

        if len(all_violations) > 5:
            print(f"\n   ... and {len(all_violations) - 5} more violations")

        return 0

    # Handle analyze
    if args.cmd == "analyze":
        try:
            from .ai_suggestions import get_schema_analysis
        except ImportError:
            print(
                "error: openai package not installed. "
                "Run: pip install openai",
                file=sys.stderr,
            )
            return 2

        if not args.schema.exists():
            print(f"error: schema file not found: {args.schema}", file=sys.stderr)
            return 2

        try:
            schema_text = args.schema.read_text(encoding="utf-8")
        except OSError as e:
            print(f"error: could not read schema file: {e}", file=sys.stderr)
            return 2

        print("\n" + "="*70)
        print("AI SCHEMA ANALYSIS & RECOMMENDATIONS")
        print("="*70)
        print()

        try:
            analysis = get_schema_analysis(schema_text, api_key=args.api_key)
            print(analysis)
        except Exception as e:
            print(f"error: could not analyze schema: {e}", file=sys.stderr)
            return 2

        return 0

    # Handle validate
    if args.cmd == "validate":
        # Validate input paths exist
        for path in args.paths:
            if not path.exists():
                print(
                    f"error: path does not exist: {path}",
                    file=sys.stderr,
                )
                return 2

        # Load ontology
        if not args.ontology.exists():
            print(
                f"error: ontology file not found: {args.ontology}",
                file=sys.stderr,
            )
            return 2

        try:
            ontology = Ontology.from_file(args.ontology)
        except FileNotFoundError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"error: ontology format invalid: {e}", file=sys.stderr)
            return 2
        except Exception as e:
            print(f"error: could not load ontology: {e}", file=sys.stderr)
            return 2

        # Collect and validate all YAML files
        try:
            yaml_files = list(_iter_yaml_files(args.paths))
        except Exception as e:
            print(f"error: could not scan paths: {e}", file=sys.stderr)
            return 2

        if not yaml_files:
            print("warning: no YAML files found", file=sys.stderr)
            return 0

        all_violations: list[Violation] = []
        for yaml_file in yaml_files:
            try:
                violations = validate_entity_file(yaml_file, ontology)
                all_violations.extend(violations)
            except Exception as e:
                # Report but continue with other files
                print(
                    f"warning: could not validate {yaml_file}: {e}",
                    file=sys.stderr,
                )

        # Format and print output
        try:
            if args.format == "json":
                output = _format_json(all_violations)
            else:
                output = _format_text(all_violations)
        except Exception as e:
            print(f"error: could not format output: {e}", file=sys.stderr)
            return 2

        print(output)

        # Return appropriate exit code
        if all_violations:
            return 1
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())

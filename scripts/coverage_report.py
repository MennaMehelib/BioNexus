"""Generate AC8 M1 rule-to-test P/N/E coverage report from rules_register.json and tests/."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = REPO_ROOT / "src" / "bionexus" / "rules_register.json"
TESTS_ROOT = REPO_ROOT / "tests"

M1_IMPLEMENTED_RULES = (
    "G-01",
    "G-02",
    "G-03",
    "G-04",
    "M-01",
    "M-02",
    "M-03",
    "M-04",
    "R-01",
    "R-02",
    "R-05",
    "R-06",
    "J-04",
    "J-05",
    "V-02",
)
_TEST_NAME_RE = re.compile(r"^test_([A-Z])_?(\d{2})_([PNE])_")


def collect_coverage(
    register_path: Path = REGISTER_PATH,
    tests_root: Path = TESTS_ROOT,
) -> dict:
    register = json.loads(register_path.read_text(encoding="utf-8"))
    accept_m1_ids = [r["id"] for r in register if r["status"] == "ACCEPT_M1"]

    counts: Counter[tuple[str, str]] = Counter()
    for test_file in sorted(tests_root.rglob("test_*.py")):
        tree = ast.parse(test_file.read_text(encoding="utf-8"), filename=str(test_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                match = _TEST_NAME_RE.match(node.name)
                if match:
                    rule_id = f"{match.group(1)}-{match.group(2)}"
                    counts[(rule_id, match.group(3))] += 1

    m1_implemented = {}
    failing = []
    for rid in M1_IMPLEMENTED_RULES:
        p = counts[(rid, "P")]
        n = counts[(rid, "N")]
        e = counts[(rid, "E")]
        ok = p >= 1 and n >= 1 and e >= 1
        m1_implemented[rid] = {"P": p, "N": n, "E": e, "ac8_pass": ok}
        if not ok:
            failing.append(rid)

    not_scheduled = {}
    m1_set = set(M1_IMPLEMENTED_RULES)
    for rid in accept_m1_ids:
        if rid not in m1_set:
            not_scheduled[rid] = {
                "P": counts[(rid, "P")],
                "N": counts[(rid, "N")],
                "E": counts[(rid, "E")],
                "status": "not_scheduled_in_M1",
            }

    return {
        "m1_implemented": m1_implemented,
        "not_scheduled_in_M1": not_scheduled,
        "ac8_pass": len(failing) == 0,
        "failing_rules": failing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BioNexus M1 rule P/N/E test coverage report")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    report = collect_coverage()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=False))
    else:
        print("M1-implemented ACCEPT_M1 rules (AC8 requires P>=1, N>=1, E>=1):")
        print(f"{'Rule':<6} {'P':>4} {'N':>4} {'E':>4}  Status")
        for rid, entry in report["m1_implemented"].items():
            status = "PASS" if entry["ac8_pass"] else "FAIL"
            print(f"{rid:<6} {entry['P']:>4} {entry['N']:>4} {entry['E']:>4}  {status}")
        print("\nACCEPT_M1 rules not scheduled in M1 (M2-M4):")
        for rid, entry in report["not_scheduled_in_M1"].items():
            print(
                f"{rid:<6} {entry['P']:>4} {entry['N']:>4} {entry['E']:>4}  {entry['status']}"
            )
        print(f"\nAC8 overall: {'PASS' if report['ac8_pass'] else 'FAIL'}")

    return 0 if report["ac8_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

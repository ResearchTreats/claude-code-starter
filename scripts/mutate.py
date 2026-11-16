"""Mutation check: break each piece of a change on purpose and confirm a test fails.
Usage (repo root): python scripts/mutate.py SPEC.py [pytest args...]

SPEC.py defines MUTANTS = [(path, old, new), ...]; each `old` must occur exactly once
in its file. Every file is restored after each run, even on error. Exit code 1 when a
mutant survives (no test noticed the break) - that piece is untested.

Example (this repo):
    python scripts/mutate.py examples/spec_push_guard.py tests/test_push_guard.py -q
"""
import runpy
import subprocess
import sys
from pathlib import Path


def run(mutants, pytest_args, root: Path = Path(".")) -> list:
    """[(mutant, killed, last_line)] for each mutant, files restored after each."""
    results = []
    for path, old, new in mutants:
        p = root / path
        keep = p.read_text(encoding="utf-8")
        if keep.count(old) != 1:
            raise SystemExit(f"{path}: the text to mutate occurs {keep.count(old)} times, "
                             f"not once: {old[:60]!r}")
        try:
            p.write_text(keep.replace(old, new), encoding="utf-8")
            r = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider",
                                *pytest_args], capture_output=True, text=True, cwd=root)
            lines = (r.stdout or "").strip().splitlines()
            results.append(((path, old, new), r.returncode != 0, lines[-1] if lines else ""))
        finally:
            p.write_text(keep, encoding="utf-8")
    return results


def main() -> int:
    spec, pytest_args = sys.argv[1], sys.argv[2:] or ["-q"]
    mutants = runpy.run_path(spec)["MUTANTS"]
    results = run(mutants, pytest_args)
    for (path, _old, new), killed, last in results:
        print(f"{'KILLED  ' if killed else 'SURVIVED'} {path}: {new[:50]!r} -> {last}")
    survived = sum(1 for _m, killed, _l in results if not killed)
    print(f"{len(results) - survived}/{len(results)} killed")
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())

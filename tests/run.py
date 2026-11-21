#!/usr/bin/env python3
"""Build Linf and exercise its output contracts without a shell harness."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"


def execute(command, cwd=TESTS, env=None, timeout=180):
    return subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                          text=True, encoding="utf-8", errors="replace",
                          capture_output=True, timeout=timeout)


def check(condition, label, result=None):
    if not condition:
        detail = "" if result is None else f"\nexit={result.returncode}\n{result.stdout}\n{result.stderr}"
        raise AssertionError(label + detail)
    print(f"PASS {label}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finc", default=os.environ.get("FINC", "finc"))
    parser.add_argument("--fin-libs", default=os.environ.get("SDK_LIB", os.environ.get("FIN_LIBS", "")))
    parser.add_argument("--opt", choices=("-O0", "-O2"), default=os.environ.get("OPT", "-O0"))
    args = parser.parse_args()
    compiler = Path(shutil.which(args.finc) or args.finc).resolve()
    env = dict(os.environ, FINC=str(compiler), PYTHONUTF8="1")
    if args.fin_libs:
        env["FIN_LIBS"] = str(Path(args.fin_libs).resolve())
    suffix = ".exe" if os.name == "nt" else ""
    with tempfile.TemporaryDirectory(prefix="linf-check-") as directory:
        binary = Path(directory) / f"linf{suffix}"
        build = [compiler, ROOT / "src/linf.fin", args.opt, "-o", binary, "-I", ROOT / "src"]
        if args.fin_libs:
            build += ["--fin-libs", args.fin_libs]
        result = execute(build, ROOT, env)
        check(result.returncode == 0, "build", result)

        def run(*options):
            result = execute([binary, "check", "--finc", compiler, *options], env=env)
            check(result.stdout == "", "stdout silent", result)
            return result

        result = run("fixture_ok.fin")
        check(result.returncode == 0, "ok-rc", result)
        check(len(result.stderr.splitlines()) == 1, "ok-one-line", result)
        check('"kind":"summary","errors":0,"warnings":0,"exitCode":0,"status":"ok"' in result.stderr,
              "ok-clean", result)

        result = run("fixture_linted.fin")
        check(result.returncode == 1, "linted-rc", result)
        for label, fragment in (
            ("rule-line-length", '"code":"linf:line-length","message":"line is longer than 100 columns","file":"fixture_linted.fin","line":5'),
            ("rule-delete-new", '"code":"linf:delete-without-new"'),
            ("rule-unused-import", "import 'read_to_string' is never used"),
            ("linted-summary", '"warnings":3,"exitCode":1'),
        ):
            check(fragment in result.stderr, label, result)

        result = run("fixture_bad.fin")
        check(result.returncode == 1, "bad-rc", result)
        check("expected ';'\"" in result.stderr, "bad-forward", result)
        check('"errors":1' in result.stderr and '"exitCode":1,"status":"failed"' in result.stderr,
              "bad-summary", result)
        result = run("fixture_indexed.fin")
        check(result.returncode == 1, "indexed-rc", result)
        check('"code":"linf:unchecked-index","message":"indexing without blame in this file","file":"fixture_indexed.fin","line":7' in result.stderr,
              "rule-unchecked-index", result)
        check('"warnings":1,"exitCode":1' in result.stderr, "indexed-summary", result)
        result = run("fixture_blamed.fin")
        check(result.returncode == 0, "blamed-clean", result)
        check("unchecked-index" not in result.stderr, "blamed-silent", result)

        result = run("--format", "gcc", "fixture_linted.fin")
        check("fixture_linted.fin:5:1: warning: line is longer than 100 columns" in result.stderr,
              "gcc-lane", result)
        result = run("--format", "actions", "fixture_linted.fin")
        check("::warning file=fixture_linted.fin,line=5,col=1::line is longer than 100 columns" in result.stderr,
              "actions-lane", result)
        check('"exitCode":1' in result.stderr, "actions-summary", result)
        result = run("--format", "sarif", "fixture_linted.fin")
        check(result.returncode == 1, "sarif-rc", result)
        document = json.loads(result.stderr)
        sarif = document["runs"][0]
        check(document["version"] == "2.1.0" and sarif["tool"]["driver"]["name"] == "linf"
              and len(sarif["tool"]["driver"]["rules"]) == 5 and len(sarif["results"]) == 3
              and sarif["results"][0]["ruleId"] == "linf:line-length", "sarif-doc", result)
        result = run("--format", "sarif", "fixture_ok.fin")
        check(len(json.loads(result.stderr)["runs"][0]["results"]) == 0, "sarif-clean", result)
        check(result.returncode == 0, "sarif-ok-rc", result)

        for label, options, fragment in (
            ("bad-lane", ["--format", "yaml", "fixture_ok.fin"], "unknown --format"),
            ("no-paths", [], "no paths"),
            ("bad-option", ["--nope", "fixture_ok.fin"], "unknown option"),
        ):
            result = run(*options)
            check(fragment in result.stderr, label + "-msg", result)
            check(result.returncode == 2, label + "-rc", result)
        result = run("fixture_ok.fin", "fixture_bad.fin", "fixture_linted.fin")
        check('"errors":1,"warnings":3,"exitCode":1' in result.stderr, "multi-totals", result)
        result = run("--finc")
        check(result.returncode == 2 and "missing value" in result.stderr, "missing-option-value", result)
        result = execute([binary, "--help"], env=env)
        check(result.returncode == 0 and "usage: linf check" in result.stdout, "help", result)
        result = execute([binary, "--version"], env=env)
        check(result.returncode == 0 and result.stdout.strip() == "linf", "version", result)
        result = run("--", "fixture_ok.fin")
        check(result.returncode == 0, "option-terminator", result)

        result = execute([sys.executable, "-I", TESTS / "regressions.py", binary, compiler], env=env, timeout=300)
        print(result.stdout, end="", flush=True)
        check(result.returncode == 0, "production-regressions", result)
    print("ALL LINF SELF-CHECKS PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Executable contract/import regressions, using a controlled compiler subprocess."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

BIN = str(Path(sys.argv[1]).resolve())
FINC = str(Path(sys.argv[2]).resolve())
COUNT = 0


def check(condition, label):
    global COUNT
    assert condition, label
    COUNT += 1
    print(f"PASS regression {label}")


def summary(errors=0, warnings=0, code=0):
    return dict(kind="summary", errors=errors, warnings=warnings, exitCode=code,
                status="failed" if code else "ok")


def diagnostic(message, severity="warning", file="input.fin", line=1):
    return dict(kind="diagnostic", severity=severity, code=None, message=message,
                file=file, line=line, column=2 if line else 0,
                endLine=line, endColumn=3 if line else 0, help=None, attribution=None)


def records(*rows):
    return "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows)


with tempfile.TemporaryDirectory(prefix=".linf-regressions-", dir=Path(__file__).parent) as directory:
    root = Path(directory)
    fake = root / "compiler space ' quote $(touch compiler-pwn) `touch backtick-pwn`"
    fake.write_text('''#!/usr/bin/env python3
import json, os
from pathlib import Path
import sys
assert sys.argv[2:] == ["--diagnostics=json", "--color=never"], sys.argv
if os.environ.get("LINF_ARGV_LOG"):
    Path(os.environ["LINF_ARGV_LOG"]).write_text(json.dumps(sys.argv[1:]))
p = Path(sys.argv[1])
sys.stderr.write(Path(str(p) + ".jsonl").read_text())
rc = Path(str(p) + ".rc")
sys.exit(int(rc.read_text()) if rc.exists() else 0)
''')
    fake.chmod(0o755)
    source = root / "clean.fin"
    source.write_text("fun main() <noret> {}\n")

    def prepare(text, target=source, rc=0):
        Path(str(target) + ".jsonl").write_text(text)
        Path(str(target) + ".rc").write_text(str(rc))

    def run(lane="contract", targets=None, compiler=fake):
        env = os.environ.copy()
        env["LINF_ARGV_LOG"] = str(root / "argv.json")
        result = subprocess.run([BIN, "check", "--finc", str(compiler), "--format", lane,
                                 *(str(p) for p in (targets or [source]))],
                                cwd=root, env=env, capture_output=True, text=True, timeout=45)
        assert result.stdout == "", (lane, result.stdout)
        return result

    def jsonl(result):
        try:
            rows = [json.loads(line) for line in result.stderr.splitlines()]
        except ValueError:
            raise AssertionError((result.returncode, result.stderr))
        assert rows[-1]["kind"] == "summary", rows
        assert sum(row.get("kind") == "summary" for row in rows) == 1, rows
        assert rows[-1]["exitCode"] == result.returncode, rows[-1]
        return rows

    future = ' { "kind" : "future-event", "nested": {"kind":"summary", "line":900}, "array":[null,true,1.2e-3] }'
    messages = [diagnostic('first "quoted" \\ slash', line=4),
                diagnostic("second café \U0001f642", file="other.fin", line=7),
                diagnostic("invocation problem", severity="error", file=None, line=0)]
    text = records(messages[0]) + future + "\n" + records(*messages[1:], summary(1, 2, 1))
    prepare(text)
    result = run()
    rows = jsonl(result)
    check(result.returncode == 1 and future in result.stderr.splitlines(), "unknown kind forwarded verbatim")
    check(rows[:-1] == [messages[0], json.loads(future), *messages[1:]], "distinct compiler records retained")
    check(rows[-1]["errors"] == 1 and rows[-1]["warnings"] == 2, "compiler totals")
    result = run("gcc")
    check('input.fin:4:2: warning: first "quoted" \\ slash' in result.stderr
          and "other.fin:7:2: warning: second café \U0001f642" in result.stderr,
          "gcc record boundaries and Unicode escapes")
    check("finc: error: invocation problem" in result.stderr and "line:0" not in result.stderr,
          "null file remains locationless")
    result = run("sarif")
    sarif = json.loads(result.stderr)["runs"][0]["results"]
    check([r["message"]["text"] for r in sarif] == [d["message"] for d in messages], "sarif distinct records")
    check("locations" not in sarif[-1], "sarif null location")
    result = run("actions")
    check("::warning file=other.fin,line=7,col=2::second café" in result.stderr
          and "::error ::invocation problem" in result.stderr, "actions distinct records and null location")

    nested = diagnostic("outer", line=8)
    nested = {"extra": {"severity": "error", "message": "wrong", "line": 999}, **nested}
    prepare(records(nested, summary(0, 1, 1)))
    check("input.fin:8:2: warning: outer" in run("gcc").stderr, "nested keys do not shadow fields")
    prepare(records(diagnostic("future severity", "fatal"), summary()))
    result = run()
    check(result.returncode == 1 and jsonl(result)[-1]["errors"] == 1, "unknown severity treated as error")

    invalid = {
        "empty": "",
        "plain-text": "compiler crashed\n",
        "truncated-record": '{"kind":"summary"',
        "truncated-after-comma": '{"kind":"summary",',
        "missing-fields": '{"kind":"summary"}\n',
        "wrong-type": records({**summary(), "errors": "0"}),
        "negative-count": records(summary(-1)),
        "overflow-count": records(summary(2147483648)),
        "fraction-count": records(summary(0.5)),
        "bad-exit": records(summary(code=4)),
        "bad-status": records({**summary(), "status": "failed"}),
        "multiple-summary": records(summary(), summary()),
        "record-after-summary": records(summary(), diagnostic("late")),
        "unknown-after-summary": records(summary(), {"kind": "future"}),
        "trailing-garbage": records(summary()).rstrip() + "junk\n",
        "duplicate-field": '{"kind":"summary","errors":0,"errors":1,"warnings":0,"exitCode":0,"status":"ok"}\n',
        "leading-zero": '{"kind":"summary","errors":00,"warnings":0,"exitCode":0,"status":"ok"}\n',
        "bad-escape": records(diagnostic("bad")).replace('"bad"', '"bad\\q"') + records(summary()),
        "bad-surrogate": records(diagnostic("bad")).replace('"bad"', '"\\ud800"') + records(summary()),
        "embedded-nul": records(diagnostic("bad\0suffix"), summary()),
    }
    for name, payload in invalid.items():
        prepare(payload)
        result = run()
        rows = jsonl(result)
        check(result.returncode == 2 and any(r.get("code") == "linf:plumbing" for r in rows), name)
    prepare(records(summary()).rstrip("\n"))
    check(run().returncode == 0, "complete final record needs no newline")
    prepare(records(summary(code=3)), rc=0)
    check(run().returncode == 3, "valid summary is authoritative")
    prepare("", rc=3)
    check(run().returncode == 3, "compiler failure fallback")

    second = root / "second.fin"
    second.write_text(source.read_text())
    prepare(records(summary()))
    prepare("", second)
    for targets in ([source, second], [second, source]):
        result = run(targets=targets)
        check(result.returncode == 2 and jsonl(result)[-1]["errors"] == 1,
              f"missing summary cannot hide in multipath {targets[0].name}")
    prepare(records(summary(code=3)), second)
    prepare("", source)
    check(run(targets=[source, second]).returncode == 3, "compiler failure outranks plumbing")

    special = root / 'source space \' " $(touch source-pwn) `touch source-backtick-pwn`.fin'
    special.write_text(source.read_text())
    prepare(records(summary()), special)
    result = run(targets=[special])
    check(result.returncode == 0, "literal executable and source paths")
    check(json.loads((root / "argv.json").read_text())[0] == str(special), "argv exact round trip")
    check(not any((root / name).exists() for name in
                  ["compiler-pwn", "backtick-pwn", "source-pwn", "source-backtick-pwn"]), "no shell side effects")

    many = [diagnostic(f"warning-{i}", line=i + 1) for i in range(600)]
    prepare(records(*many, summary(0, 600, 1)))
    for lane in ["contract", "gcc", "actions", "sarif"]:
        result = run(lane)
        if lane == "sarif":
            emitted = json.loads(result.stderr)["runs"][0]["results"]
            good = len(emitted) == 600 and emitted[-1]["message"]["text"] == "warning-599"
        elif lane == "contract":
            rows = jsonl(result)
            good = len(rows) == 601 and rows[-1]["warnings"] == 600
        else:
            good = len(result.stderr.splitlines()) == 601 and "warning-599" in result.stderr
        check(result.returncode == 1 and good, f"600 warnings {lane}")

    # A deliberate resource ceiling must be loud, even if the pool is full
    # before a missing-summary plumbing diagnostic needs to be recorded.
    prepare(records(*(diagnostic("overflow") for _ in range(65537))))
    result = run("sarif")
    emitted = json.loads(result.stderr)["runs"][0]["results"]
    check(result.returncode == 2 and len(emitted) == 65537
          and emitted[-1]["ruleId"] == "linf:plumbing"
          and "incomplete" in emitted[-1]["message"]["text"], "resource ceiling preserves plumbing failure")

    def imports(name, code, expected, real=True):
        target = root / f"{name}.fin"
        target.write_text(code)
        prepare(records(summary()), target)
        result = run(targets=[target], compiler=FINC if real else fake)
        rows = jsonl(result)
        names = [r["message"].split("'")[1] for r in rows if r.get("code") == "linf:unused-import"]
        check(names == expected and rows[-1]["errors"] == 0, name)

    imports("module-alias-used", "import stdio::std as io;\nfun main() <noret> { io.printf(\"ok\"); }\n", [])
    imports("module-alias-unused", "import stdio::std as io;\nfun main() <noret> {}\n", ["io"])
    imports("plain-module", "import stdio;\nfun main() <noret> {}\n", ["stdio"])
    imports("before-final-import", 'import { printf } from stdio::std;\nfun main() <noret> { printf("ok"); }\nimport { len } from strings::std;\n', ["len"])
    imports("wildcard", "import * from stdio::std;\nfun main() <noret> {}\n", [])
    imports("alias-then-selected", 'import stdio::std as io;\nimport { len } from strings::std;\nfun main() <noret> { printf("%d", len("ok")); }\n', ["io"])
    imports("repeat-name", 'import { printf } from stdio::std;\nimport { printf } from stdio::std;\nfun main() <noret> {}\n', ["printf", "printf"])
    imports("comments-not-use", 'import { len } from strings::std;\n// len is mentioned\nfun main() <noret> { printf("len"); }\n', ["len"])
    module = root / "local.fin"
    module.write_text("pub fun answer() <int> { return 42; }\n")
    imports("quoted-module", 'import "local.fin";\nfun main() <noret> {}\n', ["local"])
    imports("quoted-module-used", 'import "local.fin";\nfun main() <int> { return local.answer(); }\n', [])
    names = [f"symbol_{i}" for i in range(300)]
    module.write_text("\n".join(f"pub fun {name}() <int> {{ return 0; }}" for name in names) + "\n")
    code = "\n".join(f'import {{ {name} }} from "local.fin";' for name in names) + "\nfun main() <noret> {}\n"
    imports("300-imports", code, names)

print(f"ALL {COUNT} LINF REGRESSION CHECKS PASS")

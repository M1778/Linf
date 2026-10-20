#!/usr/bin/env bash
# linf self-check: builds src/linf.fin and pins the behaviors the RFC demands.
# Needs a finc binary (FINC env, default /home/M1778/Fin/build/finc) and the
# fin-sdk bundle (SDK_LIB env, default ~/fin-sdk/lib, 3.2.0+).
set -u

FINC="${FINC:-/home/M1778/Fin/build/finc}"
SDK_LIB="${SDK_LIB:-$HOME/fin-sdk/lib}"
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$HERE/.linftest"

FAIL=0
pass() { echo "PASS $1"; }
defy() { echo "FAIL $1"; FAIL=1; }

"$FINC" "$HERE/../src/linf.fin" -o "$BIN" --fin-libs "$SDK_LIB" 2>/tmp/lerr || {
  echo "FAIL build"; head -5 /tmp/lerr; exit 1; }
pass build

# everything runs from the fixture dir so pinned lines/patterns hold
cd "$HERE"

linf() { "$BIN"$' \c' check >/dev/null 2>&1; }  # placeholder never used

run() { # run <lane...> into .out/.rc; stderr = lane output, stdout = silence
  OUT="$HERE/.out"; RC=0
  "$BIN" check --finc "$FINC" "$@" 2>"$OUT" 1>"$HERE/.stdout"
  RC=$?
}

# 1. clean fixture: rc 0, stdout empty, ONE summary line, nothing else
run fixture_ok.fin
[ "$RC" -eq 0 ] || defy "ok-rc"
[ ! -s "$HERE/.stdout" ] || defy "ok-stdout-silent"
[ "$(wc -l < "$OUT")" -eq 1 ] || defy "ok-one-line"
grep -qF '"kind":"summary","errors":0,"warnings":0,"exitCode":0,"status":"ok"' "$OUT" && pass "ok-clean" || defy "ok-clean"

# 2. linted fixture: rc 1, three rule findings, totals
run fixture_linted.fin
[ "$RC" -eq 1 ] && pass "linted-rc" || defy "linted-rc:$RC"
[ ! -s "$HERE/.stdout" ] || defy "linted-stdout-silent"
grep -qF '"code":"linf:line-length","message":"line is longer than 100 columns","file":"fixture_linted.fin","line":5' "$OUT" && pass "rule-line-length" || defy "rule-line-length"
grep -qF '"code":"linf:delete-without-new"' "$OUT" && pass "rule-delete-new" || defy "rule-delete-new"
grep -qF "import 'read_to_string' is never used" "$OUT" && pass "rule-unused-import" || defy "rule-unused-import"
grep -qF '"warnings":3,"exitCode":1' "$OUT" && pass "linted-summary" || defy "linted-summary"

# 3. rejected source: finc errors pass through verbatim
run fixture_bad.fin
[ "$RC" -eq 1 ] && pass "bad-rc" || defy "bad-rc:$RC"
# the decoded message ends the JSON string, so the span closes with '"'
grep -qF "expected ';'\"" "$OUT" && pass "bad-forward" || defy "bad-forward"
grep -qF '"errors":1' "$OUT" && grep -qF '"exitCode":1,"status":"failed"' "$OUT" && pass "bad-summary" || defy "bad-summary"

# 4. gcc lane: matcher-shaped first line
run --format gcc fixture_linted.fin
grep -qF "fixture_linted.fin:5:1: warning: line is longer than 100 columns" "$OUT" && pass "gcc-lane" || defy "gcc-lane"
[ ! -s "$HERE/.stdout" ] || defy "gcc-stdout-silent"

# 5. actions lane: annotation commands (consume the whole log)
run --format actions fixture_linted.fin
grep -qF '::warning file=fixture_linted.fin,line=5,col=1::line is longer than 100 columns' "$OUT" && pass "actions-lane" || defy "actions-lane"
grep -qF '"exitCode":1' "$OUT" && pass "actions-summary" || defy "actions-summary"

# 6. sarif lane: valid document, terminal artifact, mirrored rc
run --format sarif fixture_linted.fin
[ "$RC" -eq 1 ] && pass "sarif-rc" || defy "sarif-rc:$RC"
python3 - "$OUT" <<'PY' && pass "sarif-doc" || defy "sarif-doc"
import json, sys
d = json.load(open(sys.argv[1]))
r = d["runs"][0]
assert r["tool"]["driver"]["name"] == "linf"
assert len(r["tool"]["driver"]["rules"]) == 5
assert len(r["results"]) == 3
assert r["results"][0]["ruleId"] == "linf:line-length"
PY
run --format sarif fixture_ok.fin
python3 - "$OUT" <<'PY' && pass "sarif-clean" || defy "sarif-clean"
import json, sys
assert len(json.load(open(sys.argv[1]))["runs"][0]["results"]) == 0
PY
[ "$RC" -eq 0 ] || defy "sarif-ok-rc"

# 7. usage planes: 2s with named problems on stderr, stdout silent
("$BIN" check --format yaml --finc "$FINC" fixture_ok.fin 2>"$OUT" 1>"$HERE/.stdout"); RC=$?
grep -q "unknown --format" "$OUT" && pass "bad-lane-msg" || defy "bad-lane-msg"
[ "$RC" -eq 2 ] && pass "bad-lane-rc" || defy "bad-lane-rc:$RC"
[ ! -s "$HERE/.stdout" ] || defy "bad-lane-stdout-silent"

"$BIN" check --finc "$FINC" 2>"$OUT"; RC=$?
grep -q "no paths" "$OUT" && pass "no-paths-msg" && { [ "$RC" -eq 2 ] && pass "no-paths-rc" || defy "no-paths-rc:$RC"; } || defy "no-paths-msg"

"$BIN" check --nope --finc "$FINC" fixture_ok.fin 2>"$OUT"; RC=$?
grep -q "unknown option" "$OUT" && pass "bad-option-msg" && { [ "$RC" -eq 2 ] && pass "bad-option-rc" || defy "bad-option-rc:$RC"; } || defy "bad-option-msg"

# 8. multi-path totals combine
run fixture_ok.fin fixture_bad.fin fixture_linted.fin
grep -qF '"errors":1,"warnings":3,"exitCode":1' "$OUT" && pass "multi-totals" || defy "multi-totals"

rm -f "$OUT" "$HERE/.stdout" "$BIN"
if [ "$FAIL" -eq 0 ]; then echo "ALL LINF SELF-CHECKS PASS"; else echo "LINF SELF-CHECK FAILURES"; exit 1; fi

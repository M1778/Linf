# RFC: Linf — the Fin linter

Status: **v0 shipped** · Binary name: `linf` (approved, #50 §4) · Repo:
this one (`M1778/Linf`) · Plumbing contract: `finc` machine contract v3
(`docs/finc-interface-contract.md`, `kFincContractVersion = 3`)

Linf = linter for Fin. **`finc` reports compiler errors; Linf reports style
warnings** — the same source, a different layer.

## 1. Architecture (the one non-negotiable rule)

**`finc` is the source of truth. Linf never re-lexes Fin with regex, and never
forks a second lexer.** Linf builds on the machine contract the way `finn` builds on it:

1. For every path, Linf runs exactly:
   ```
   finc <path> --diagnostics=json --color=never
   ```
   (no `-o` step — with no `-o` the invocation is artifact-free and refusals
   from the contract never fire; verified below.)
2. It parses the JSONL stream on stderr: `diagnostic` objects then exactly one
   trailing `summary`. Per the contract's compatibility promise:
   keys may be added, never removed/retyped; an unknown `kind` is **kept and
   carried on**, never discarded; an unknown `severity` is treated as an
   error. A **missing summary means finc died before reporting** — that is a
   Linf plumbing failure (`exit 2`), because the contract says the summary is
   the only way to tell "finished cleanly" from "died".
   Two capture rulings the v0 binary pins:
   - the capture merges `2>&1` into the read pipe (process.fin's
     `exec_command` captures stdout), sound only because finc's stdout is
     contract-silent for every non-reserved flag — which is exactly what
     this invocation uses;
   - finc's **own summary line is the authoritative exit source** (its
     `exitCode` field), because the popen waitstatus is raw pclose
     (256×rc); the waitstatus decodes only as a fallback when no summary
     arrived (low byte nonzero = signal kill = `3`; shell 127 = `2`).
3. Linf appends **its own findings as `diagnostic` objects in the same shape**
   (`severity: "warning"` v0, `code: "linf:<rule>"` — `code` is contract-open
   to new values, `help` may carry a fix-suggestion), then emits **one
   summary** whose `errors`/`warnings` count the whole pass-through stream and
   whose `exitCode` is Linf's own. Existing JSON-diagnostic consumers can read
   Linf's output without knowing Linf.
   Field extraction is bounded to one JSONL record and reads only top-level
   contract fields. Nested additive fields are validated and skipped, nullable
   locations stay locationless, and escaped strings (including Unicode) decode
   independently. Each invocation requires exactly one valid trailing summary;
   malformed, duplicate, missing, or nonterminal summaries are plumbing failures.
   Unknown valid kinds still forward verbatim in the contract lane. The parser
   rejects nesting beyond 128 levels and decoded NUL (Fin strings cannot carry it).
   Stored diagnostics grow geometrically to 65,536; exceeding that resource ceiling
   reserves an explicit incomplete-results plumbing diagnostic and exit 2. Runtime
   allocation failure itself is not recoverable with the current Fin allocator.

## 2. Rule facts: where they come from

Ranked, most contract-true first:

1. **From finc diagnostics** — whenever finc already reports a fact (e.g. a
   checker warning), Linf does not duplicate it; it may relabel `help` only.
2. **From the real Fin scanner** (`lib/std/scanner.fin`, vendored in
   `M1778/fin-sdk` as `lib/scanner.fin`) — for keyword/token facts finc does
   not emit today (unused imports, `delete`/`new` balance). This is the
   already-landed lexer, not a re-lexing; the rules are written **in Fin**
   (dogfood per #53 Scope C: `fin-sdk/proof/linf_first_rules.fin` is the
   proven prototype for three of the five rules).
3. **From raw line/byte facts** — line length never needs a token at all.
4. **From a subprocess only for formatting** — planned (see rule 5);
   `process::std::exec_command` exists when needed.

## 3. CLI, lanes, exit codes

```
linf check [--format <lane>] [--finc <bin>] <path>...   # the only subcommand in v0
linf --help                                             # stdout, exit 0
linf --version  →  "linf"                               # stdout, exit 0
```

Options spell two tokens (`--format gcc`), following cli.fin's grammar —
the same grammar family the `linf` binary compiles against. finc's own
`--diagnostics=json` spelling is finc's native parser, a separate grammar;
the contract doc stays the plumbing source, not the spelling source.

`--format` picks the output lane; everything lands on **stderr** (stdout
stays reserved to `--help`/`--version`, mirroring finc):

| lane | shape | the hosts that eat it |
| --- | --- | --- |
| `contract` (default) | finc's JSONL forwarded VERBATIM + linf's own `diagnostic` lines + one trailing `summary` | `finn`, LSP wrappers, CI tooling — contract-compatible without knowing linf |
| `gcc` | `file:line:col: severity: message` one-liners + JSONL summary | VS Code `problemMatcher: "$gcc"`, Neovim errorformat, make/junit tooling |
| `actions` | GitHub workflow commands: `::warning file=...,line=...,col=...::msg` | GitHub Actions annotations (`note` maps to `notice`) |
| `sarif` | SARIF 2.1.0 document (five linf rules declared; finc-sourced results carry no `ruleId`) | GitHub code scanning, SARIF Viewer (VS Code/JetBrains), SonarQube ingesters |

Lane rulings the v0 binary pins:
- **contract**: finc's unknown kinds survive untouched (raw forwarding).
- **gcc/actions/sarif**: built from extractions; unknown kinds are skipped
  (a rendered line cannot represent them) — the RFC's tolerance promise
  applies to the contract lane.
- **sarif**: the document is the terminal artifact — NO trailing JSONL
  summary line, because SARIF consumers choke on it. The three line lanes
  keep the summary.
- Location-less diagnostics (finc flag refusals, linf plumbing) render as
  `linf: severity: message` (or `finc:` when finc-sourced) in the gcc lane
  and omit `file=` in the actions lane; SARIF omits `locations`.

Exit codes **mirror finc's meanings, adapted to a linter**:

| Code | Meaning | Contract analogue |
| --- | --- | --- |
| `0` | finc clean, no Linf findings | finc `0` |
| `1` | Linf findings, **or** finc rejected the source (pass-through shows why) | finc `1` |
| `2` | Bad usage, unreadable path, or **missing/broken summary** (plumbing) | finc `2` |
| `3` | finc itself failed — propagate: "a bug in finc, not in the source or linf" | finc `3` |

linf's own failures (unknown option handled by cli.fin's message, no paths,
unknown lane, unreadable path with no finc 1, missing summary) are usage- and
plumbing-plane `2`s, reported as contract JSONL on stderr like everything
else. An exit code cannot distinguish "clean" from "crashed"; the summary is
what consumers trust, per the contract.

## 4. Rules — v0 list (five, frozen until a ruling expands it)

| rule | code | level | detection | status |
| --- | --- | --- | --- | --- |
| line length > 100 | `linf:line-length` | warning | raw lines | **shipped** (linf v0 binary; proven earlier in fin-sdk) |
| unused import | `linf:unused-import` | warning | scanner (name never spelled after its import) | **shipped** (linf v0 binary; finc emits no unused-import fact, so this is linf's own) |
| `delete` without `new` | `linf:delete-without-new` | warning | scanner (file says `delete`, never `new`) | **shipped** (linf v0 binary; v0 file-level) |
| unchecked index without `blame` | `linf:unchecked-index` | warning | scanner: a postfix bracket (`expr[...]` — ident/`)`/`]`/literal before it, never type/`new` spellings) in a file with no `blame` token at all; honest wording until a semantic pass exists | **shipped** (linf v0 binary; v0 file-level) |
| `fin fmt` drift | `linf:fmt-drift` | warning | subprocess via `finfmt --check` | **pending** — `finfmt --check` ships in Fin now: exit `1` with a diff on whitespace drift (indent, tab indent, trailing WS probed); it deliberately skips intra-line spacing (evidence below) — and the rule's subprocess wiring did not land in v0 |

Non-goals v0: no autofixes, no per-project config files (thresholds frozen
here until a ruling), no parallel jobs, no finn packaging (that waits for the
registry).

## 5. Stages

1. **RFC + scaffold** — done (`b74f3a0`): contract v3 pinned, evidence gathered.
2. **Rules stage** — done in the same landing: the three scanner rules and
   line length live in `src/linf.fin` (written in Fin against the fin-sdk
   bundle, which grew `cli`, `process`, `json`, `hashmap` by 3.2.0 to carry
   them).
3. **Binary stage** — done at v0 (`a846ab2`, rule 4 at `697e2b0`):
   `src/linf.fin` builds into the `linf` binary; four lanes, exit mirror,
   stream discipline, multi-path totals — all pinned by the 28 asserts in
   `tests/run.sh`.
4. **Package stage** — pending: `finn` packaging once the registry supports it.

Stages 1–3 are done, stage 4 is pending. Each landing arrives with tests that
run against a real `build/finc`.

## 6. Versioning

`VERSION` major tracks `kFincContractVersion` (same policy as `M1778/fin-sdk`):
current contract 3 → `3.0.0`. Minor/patch: rule additions/fixes. A linf built
against contract N is not promised to parse contract N+1 streams unchanged —
but the unknown-kind/severity rules above keep it *forward-tolerant*.

## 7. Evidence (all at Fin `a6b4b67`, contract 3)

- `finc ok.fin --diagnostics=json --color=never` → exit 0, stderr exactly
  `{"kind":"summary","errors":0,"warnings":0,"exitCode":0,"status":"ok"}`,
  stdout empty, **no build artifacts left in cwd**.
- `finc bad.fin --diagnostics=json --color=never` (a `;` only after the
  closing brace, as reproduced by `tests/fixture_bad.fin`) → exit 1 with
  an error diagnostic carrying `file/line/column/endLine/endColumn` + summary
  `status:"failed"` — the shape Linf appends to, verbatim key set.
- `-o` + `--diagnostics=json` → the contract's refusal diagnostic + summary
  `exitCode: 2`, as documented.
- `finfmt --check` (shipped in Fin) exits `1` with a unified diff on
  whitespace drift — indentation and tab indent are the probed cases;
  intra-line spacing stays `0`, skipped on purpose in the formatter's canon.
  Rule 5's wiring rides `process::std` when it lands.

Evidence of the v0 binary (all at Fin `a6b4b67`, contract 3, `linf` built
from `src/linf.fin` against `fin-sdk` 3.2.0):
- `linf check fixture_ok.fin` → exit 0, stdout **0 bytes**, stderr exactly
  `{"kind":"summary","errors":0,"warnings":0,"exitCode":0,"status":"ok"}`.
- `linf check fixture_linted.fin` → exit 1 with exactly three linf findings
  (`linf:line-length` @5:1, `linf:delete-without-new` @9:1,
  `linf:unused-import` @1:1) and summary
  `{"kind":"summary","errors":0,"warnings":3,"exitCode":1,"status":"failed"}`.
- `linf check fixture_bad.fin` → finc's error forwarded verbatim in the
  contract lane; `--format gcc` renders `fixture_bad.fin:1:27: error:
  expected ';'` (the escaped `';'` unescaped through `json_decode_str`);
  exit 1, summary `errors:1`.
- `--format sarif` on the linted fixture: 5 rules declared, 3 results with
  `ruleId`/`level`/`region` correct (`region` inside
  `locations[0].physicalLocation`); on the clean fixture: `results: []`,
  exit 0; no trailing summary line in the document.
- `--format actions`: `::warning file=fixture_linted.fin,line=5,col=1::...`.
- `linf check fixture_indexed.fin` (postfix `chars[i]`, no `blame` anywhere)
  → exactly one finding `linf:unchecked-index` @7:1, exit 1,
  summary `warnings:1 exitCode:1`; the same shape WITH a `blame` line
  (`fixture_blamed.fin`) → clean, exit 0, no finding.
- multi-path `check ok bad linted` → one combined summary
  `errors:1 warnings:3`.
- usage planes: unknown format → `linf: unknown --format
  'yaml' (use contract|gcc|actions|sarif)` exit 2; no paths → exit 2;
  unknown option → cli.fin's `unknown option '--nope'` exit 2 — all
  contract JSONL or plain usage shapes on stderr, stdout untouched.

## 8. IDE + CI integration

`INTEGRATION.md` carries the copy-paste harnesses: a VS Code `tasks.json`
task on the `gcc` lane (`problemMatcher: "$gcc"`, and `fin-vscode` ships a
native extension once its grammar lands per #50), Neovim
`makeprg`/`errorformat`, GitHub Actions annotation runs, GitHub code
scanning via the SARIF lane, and SARIF viewers (VS Code / JetBrains
plugins).

`linf` stays a plain CLI by design. Editors get native diagnostics through
the `finls` LSP wrapper (#50 §5), which parses the `contract` lane; the
editor-side extension itself is owned by `fin-vscode` (#50 §1/§7).

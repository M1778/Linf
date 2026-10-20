# RFC: Linf — the Fin linter

Status: **draft, scaffolded** · Binary name: `linf` (approved, #50 §4) · Repo:
this one (`M1778/Linf`) · Plumbing contract: `finc` machine contract v3
(`docs/finc-interface-contract.md`, `kFincContractVersion = 3`)

Linf = linter for Fin. **`finc` reports compiler errors; Linf reports style
warnings** — the same source, a different layer, never a second implementation
of the language.

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
3. Linf appends **its own findings as `diagnostic` objects in the same shape**
   (`severity: "warning"` v0, `code: "linf:<rule>"` — `code` is contract-open
   to new values, `help` may carry a fix-suggestion), then emits **one
   summary** whose `errors`/`warnings` count the whole pass-through stream and
   whose `exitCode` is Linf's own. Existing JSON-diagnostic consumers can read
   Linf's output without knowing Linf.

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

## 3. CLI + exit codes

```
linf check [paths...]     # style warnings; the only subcommand in v0
linf --help               # stdout, exit 0
linf --version  →  "linf <semver> (contract <int>)"
```

stdout is reserved for `--help`/`--version` only — everything else is
JSONL on stderr, mirroring finc's stream discipline.

Exit codes **mirror finc's meanings, adapted to a linter**:

| Code | Meaning | Contract analogue |
| --- | --- | --- |
| `0` | finc clean, no Linf findings | finc `0` |
| `1` | Linf findings, **or** finc rejected the source (pass-through shows why) | finc `1` |
| `2` | Bad usage, unreadable path, or **missing/broken summary** (plumbing) | finc `2` |
| `3` | finc itself failed — propagate: "a bug in finc, not in the source or linf" | finc `3` |

An exit code cannot distinguish "clean" from "crashed"; the summary is what
consumers trust, per the contract.

## 4. Rules — v0 list (five, frozen until a ruling expands it)

| rule | code | level | detection | status |
| --- | --- | --- | --- | --- |
| line length > 100 | `linf:line-length` | warning | raw lines | **proven** (fin-sdk proof, one warn/file) |
| unused import | `linf:unused-import` | warning | scanner (name never spelled after its import) | **proven** (fin-sdk proof) |
| `delete` without `new` | `linf:delete-without-new` | warning | scanner (file says `delete`, never `new`) | **proven** (fin-sdk proof; v0 file-level) |
| unchecked index without `blame` | `linf:unchecked-index` | warning | scanner (bracket-index in a file with no `blame`); honest wording until a semantic pass exists | planned |
| `fin fmt` drift | `linf:fmt-drift` | warning | subprocess byte-compare vs `finfmt` | **blocked on `finfmt`**: its `--check` exits `0` on drift today (evidence below) |

Non-goals v0: no autofixes, no per-project config files (thresholds frozen
here until a ruling), no parallel jobs, no finn packaging (that waits for the
registry).

## 5. Stages

1. **This commit** — RFC + repo scaffold; contract v3 pinned; evidence gathered.
2. **Rules stage** — the fin-sdk proof graduates: rules live here, still
   written in Fin against the SDK bundle.
3. **Binary stage** — `linf` CLI: contract pass-through + rule findings in one
   JSONL stream, exit mirror honored, tested against `bad.fin`-class probes.
4. **Package stage** — `finn` packaging once the registry supports it.

Stages 2–4 land as `linf` work in this repo; each lands only with tests that
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
- `finc bad.fin --diagnostics=json --color=never` (missing `;`) → exit 1 with
  an error diagnostic carrying `file/line/column/endLine/endColumn` + summary
  `status:"failed"` — the shape Linf appends to, verbatim key set.
- `-o` + `--diagnostics=json` → the contract's refusal diagnostic + summary
  `exitCode: 2`, as documented.
- `finfmt --check` currently exits `0` even on drifted spellings (e.g.
  `fun main ()` spacing) — so rule 5's "planned" status is graded on
  that, not on optimism; `finfmt` is invoked from `process::std` when the
  check mode is real.

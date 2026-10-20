# Linf

The linter for Fin: `finc` = compiler errors, **`linf` = style warnings**.
Name and binary spellings are approved (M1778/Fin#50 §4); the `linf` v0
binary is real and shipped in this repo, written **in Fin** against the
[`M1778/fin-sdk`](https://github.com/M1778/fin-sdk) bundle.

- **Read `RFC.md` first** — architecture (build on `finc --diagnostics=json`,
  never re-lex), CLI/lanes/exit codes, the frozen five-rule v0 list, stages,
  and the evidence probes.
- **`INTEGRATION.md`** — copy-paste harnesses for VS Code (`problemMatcher:
  "$gcc"` on the `gcc` lane), Neovim (`errorformat`), GitHub Actions annotations,
  GitHub code scanning + SARIF viewers, and the LSP story (`finls` wrapper).
- **Status — v0 shipped**: `src/linf.fin` builds into the `linf` binary with
  four output lanes (`contract`/`gcc`/`actions`/`sarif`), all on stderr; the
  three scanner rules + line length live, the exit-code mirror holds
  (0 clean · 1 findings · 2 usage/plumbing · 3 finc failure propagated), and
  `tests/run.sh` pins the 28 original self-check behaviors plus 55 production
  regression checks at either `OPT=-O0` (default) or `OPT=-O2`. `finn` packaging
  (RFC §5 stage 4) is still pending.
- **Try it**:
  ```sh
  FINC=/path/to/finc SDK_LIB=/path/to/fin-sdk/lib tests/run.sh
  # or by hand:
  finc src/linf.fin -o linf --fin-libs /path/to/fin-sdk/lib
  ./linf check path/to/your.fin --format gcc
  ```
- **Rules status**: line-length / unused-import / delete-without-new /
  unchecked-index shipped (four of five); `fmt-drift` blocked until
  `finfmt --check`'s exit code is drift-truthful (RFC §4 records the probe).
- **Production behavior**: compiler/source paths are literal POSIX shell
  arguments; every invocation must provide exactly one valid trailing summary.
  Unknown record kinds survive verbatim in `contract`. Diagnostics grow beyond
  256; 65,536 stored findings trigger an explicit incomplete-results plumbing
  error (exit 2), not silent truncation. Imports track aliases and declaration
  boundaries without the former 32-name cap.
- **Limits**: Linux CLI/process support follows the SDK. Fin allocations have no
  recoverable out-of-memory path; the explicit diagnostic ceiling is not an OOM
  guarantee. JSON nesting beyond 128 levels and decoded NUL strings fail as
  plumbing; command-line arguments cannot contain NUL. Import use remains a
  token-spelling heuristic, not scope/ownership analysis. Frozen SDK scanner and
  CLI allocation/argument limits remain outside this repository.
- **Contract** — plumbing pinned to the finc machine contract v3
  (`kFincContractVersion`); `VERSION` major tracks it, same policy as
  `fin-sdk` (currently 3.0.0).

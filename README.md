# Linf

The linter for Fin: `finc` = compiler errors, **`linf` = style warnings**.
Name and binary spellings are approved (M1778/Fin#50 §4); this repo is the
scaffold.

- **Read `RFC.md` first** — architecture (build on `finc --diagnostics=json`,
  never re-lex), CLI + exit codes, the frozen five-rule v0 list, and the
  evidence probes.
- **Status** — scaffold only. The `linf` binary does not exist yet; stages
  live in the RFC §5. The three token rules already have a *proven
  prototype*: `linf_first_rules.fin` in
  [`M1778/fin-sdk`](https://github.com/M1778/fin-sdk) — line-length,
  unused-import, delete-without-new, written in Fin against the SDK's own
  scanner and diagnostics, exiting 1 on findings.
- **Contract** — plumbing pinned to the finc machine contract v3
  (`kFincContractVersion`); `VERSION` major tracks it, same policy as
  `fin-sdk`.
- **fmt-drift rule** — blocked until `finfmt --check`'s exit code is
  drift-truthful (RFC §4 records the probe); nothing blocks rules 1–4.

# Integrating linf with IDEs and CI

`linf` emits four lanes (RFC §3), all on stderr. Pick the one your host
consumes; the contract JSONL lane is what programmatic consumers parse.
Each input's compiler stream must end in exactly one valid summary. Malformed
streams fail with a `linf:plumbing` diagnostic (exit 2); valid unknown kinds are
forwarded verbatim only in `contract`. Never infer success from missing output.
The 65,536 stored-diagnostic ceiling is also an explicit incomplete-results
plumbing failure, including in SARIF; consumers must check the process exit.

## VS Code — works today, no extension required

`tasks.json` in any Fin workspace; the `$gcc` matcher eats the `--format gcc`
lane:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "linf",
      "type": "shell",
      "command": "linf",
      "args": ["check", "--finc", "finc", "--format", "gcc", "${file}"],
      "options": { "cwd": "${workspaceFolder}" },
      "problemMatcher": "$gcc",
      "group": { "kind": "lint" },
      "presentation": { "reveal": "silent", "clear": true, "panel": "dedicated" }
    }
  ]
}
```

`${file}` stays an array element so spaces survive. `fin-vscode` owns the
native extension (grammar per M1778/Fin#50 §1); when it lands, linf-packed
diagnostics publish through the extension instead of a task.

## Neovim (and any make-driven tooling)

```vim
autocmd FileType fin setlocal makeprg=linf\\ check\\ --finc\\ finc\\ --format\\ gcc
autocmd FileType fin setlocal errorformat=%f:%l:%c:\ %m
```

`:make` then spreads findings into the quickfix list. The severity word stays
inside the message; `%m` greps the whole tail honestly.

## GitHub Actions — annotation feed

```yaml
- name: lint
  run: linf check src/*.fin --format actions
```

`::warning`/`::error`/`::notice` commands surface as inline annotations on the
Check run. The runner reads them from the job log, so stderr output lands the
same as stdout would.

## GitHub code scanning + SARIF viewers

```yaml
- name: lint to sarif
  run: linf check src/*.fin --format sarif 2> linf.sarif
- uses: github/codeql-action/upload-sarif@v3
  with: { sarif_file: linf.sarif }
```

The same `linf.sarif` opens in SARIF Viewer (VS Code), JetBrains SARIF,
SonarQube ingesters. The SARIF document declares all five v0 rules and
carries finc's errors as tool-agnostic results (no `ruleId`).

## LSP / editors with LSP clients

`linf` stays CLI by design. The `finls` LSP wrapper (M1778/Fin#50 §5) shells
`finc`/`linf` and publishes diagnostics natively; the `contract` lane is its
parseable substrate.

## Grammar note

`linf` spells options two-token (`--format gcc`) following `cli.fin` (the
stdlib module mirrors the finc CLI grammar family); finc itself spells
`--diagnostics=json`. The RFC records the divergence — the contract doc is
linf's plumbing source, not its spelling source.

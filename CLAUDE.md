# Tamad-Strat — agent instructions

Quant validation of the Tamad-Strat 3-candle reversal strategy. Read, in order, before any work: `README.md`, `docs/STRATEGY_SPEC.md`, `docs/METHODOLOGY.md`, issue #1 (the PRD). Those four are authoritative; this file only adds process rules.

## Hard guardrails

- **Holdout lock:** never read, fetch, plot, or aggregate market data from **2025-01-01 onward** — in any experiment, notebook, or debug session — until the maintainer's explicit holdout sign-off is recorded on issue #18. This applies to you even before the experiment runner enforces it in code.
- **Data split (canonical):** training = all history through 2022-12-31 (selection happens ONLY here); test = 2023-01-01 to 2024-12-31 (confirms selections, never drives them); holdout = 2025-01-01 to present (untouched until #18 sign-off). Change only with explicit maintainer approval.
- **Every rule must earn its place:** no filters, features, or "obvious improvements" beyond what the current issue specifies. No dropping worst performers or promoting winners without an economic rationale recorded on the issue (market-logic veto).
- **Negative results are findings:** persist and report them; never delete or re-run-until-green.
- **No implementation without an issue:** work happens against issues #2–#18 in dependency order (Blocked-by fields), one at a time. The agent brief comment on each issue is the contract.

## Workflow

Issues are implemented with `/tdd` (red-green-refactor, vertical slices: one failing test → minimal code → refactor; behavior through public interfaces only). All acceptance criteria verified and full suite green before committing to `main` and closing the issue with a summary comment (metrics tables for experiment issues).

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (`dazu5/tamad-strat`), managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` at the repo root holds the domain glossary; ADRs go in `docs/adr/`. See `docs/agents/domain.md`.

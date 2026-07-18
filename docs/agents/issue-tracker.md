# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues (`dazu5/tamad-strat`). Use the `gh` CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Repo-specific notes

- Issue #1 is the PRD (parent of all implementation issues). Never close or modify it.
- Issues #2–#18 are dependency-ordered tracer-bullet slices; respect each issue's "Blocked by" field.
- Issue #18 is `ready-for-human`: the holdout unlock inside it requires explicit maintainer sign-off recorded on the issue.

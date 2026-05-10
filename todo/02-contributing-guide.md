# Contributing Guide (CLAUDE.md / CONTRIBUTING.md)

## Goal

Write a `CLAUDE.md` (for AI-assisted development) and a `CONTRIBUTING.md` (for human contributors) that codify how changes must be introduced into the codebase. This prevents direct pushes to `main` and establishes a consistent, reviewable workflow.

## Background

The project currently has no documented contribution process. Without it, developers (and AI agents) may push directly to `main`, skip CI checks, or introduce changes without review. Both files serve different audiences but share the same underlying rules.

## Acceptance Criteria

- [ ] `CLAUDE.md` exists at the repo root and instructs AI agents to:
  - Never push directly to `main`
  - Always open a pull request for any change, no matter how small
  - Run linting, type checks, and tests locally before raising a PR
  - Write a clear PR description explaining the why, not just the what
  - Follow the branch naming convention: `<type>/<short-description>` (e.g. `feat/admin-role`, `fix/login-redirect`)
- [ ] `CONTRIBUTING.md` exists at the repo root and covers:
  - Branch protection: `main` is protected; force-push and direct push are blocked
  - PR requirements: at least one approval, all CI checks must pass
  - Commit message format (Conventional Commits: `feat:`, `fix:`, `chore:`, etc.)
  - Local dev setup steps (reference `scripts/setup.sh`)
  - How to run tests (`pytest` for backend, `npm test` for frontend)
  - How to run linting (`ruff check`, `mypy`, `eslint`)
- [ ] GitHub branch protection rules are enabled on `main`:
  - Require pull request before merging
  - Require status checks to pass (link to `.github/workflows/pr-checks.yml` jobs)
  - Disallow force pushes
  - Disallow deletion

## Implementation Notes

- `CLAUDE.md` is the machine-readable contract; keep it terse and imperative
- `CONTRIBUTING.md` is human-readable; prose is fine
- Both files should be reviewed by the team before merging so everyone agrees on the rules
- Update the existing `.github/workflows/pr-checks.yml` to ensure it runs on all PRs targeting `main`, not just on push to `main`

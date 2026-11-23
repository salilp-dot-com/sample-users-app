# Contributing: branching, merging and releases

This repo uses **GitHub Flow** (trunk-based development) with **Conventional Commits** and
**automated semantic versioning**. In short: branch from `main`, open a PR, let CI pass,
squash-merge. Releases happen when you merge the release PR that the bot keeps up to date.

```
main  ──●────────●────────●──────────────●───────────●──  (always releasable, protected)
         \      /          \            /            ↑
          feat/user-search   fix/token-expiry        merge "chore(main): release 0.3.0"
          (PR, squash)       (PR, squash)            → tag v0.3.0 + GitHub Release + packages
```

## Branches

- **`main`** is the only long-lived branch. It is protected: nobody pushes to it directly,
  and every change arrives through a pull request that passed CI.
- **Work branches** are short-lived (hours to a few days), branched from the latest `main`,
  and named `<type>/<short-description>`:

  | Type       | Use for                                   | Example                    |
  |------------|-------------------------------------------|----------------------------|
  | `feat`     | A new feature                             | `feat/user-search`         |
  | `fix`      | A bug fix                                 | `fix/token-expiry`         |
  | `docs`     | Documentation only                        | `docs/deploy-guide`        |
  | `refactor` | Code change that isn't a feature or fix   | `refactor/split-auth`      |
  | `test`     | Adding or fixing tests                    | `test/cookie-auth`         |
  | `ci`/`build` | CI workflows / build and packaging      | `ci/cache-uv`              |
  | `chore`    | Anything else (deps, tooling)             | `chore/bump-vite`          |

- There are no `develop`, `release/*` or `hotfix/*` branches. A hotfix is just a `fix/…`
  branch merged like any other, followed by merging the release PR.

## Workflow

```sh
git switch main && git pull
git switch -c feat/user-search
# ...commit as often as you like; these commits are squashed on merge...
git push -u origin feat/user-search
gh pr create --fill          # then edit the title into a Conventional Commit
```

1. **Open a PR** early. Draft PRs are fine.
2. **CI must pass**: `API` (ruff lint and format check, pytest), `Web` (oxlint, tsc,
   vitest, build), `Package / Build packages` (the VM tarballs) and `Conventional PR title`.
   The packages from any CI run can be downloaded from the run's *Artifacts* to try them.
3. **Keep the branch up to date** with `main` (the *Update branch* button, or
   `git rebase origin/main`). Protection requires it, so what you tested is what lands.
4. **Squash and merge.** The PR title becomes the single commit on `main`, and the
   branch is deleted automatically.

## PR titles: Conventional Commits

The PR title must look like `<type>(<optional scope>): <summary>`. The `PR conventions`
workflow rejects anything else, because the title decides the next version:

| PR title                                    | Release on merge of the release PR |
|---------------------------------------------|------------------------------------|
| `fix(api): reject expired tokens`           | **patch**: 1.4.2 → 1.4.3           |
| `feat(web): add user search`                | **minor**: 1.4.2 → 1.5.0           |
| `feat(api)!: rename /login to /auth/login`  | **major**: 1.4.2 → 2.0.0           |
| `docs: …`, `chore: …`, `ci: …`, `test: …`, `refactor: …` | no release by themselves |

- Scopes used here: `api`, `web`, `deploy`, `ci`. They're optional.
- `!` (or a `BREAKING CHANGE:` line in the PR description) marks a breaking change.
- While the version is below 1.0.0, breaking changes bump the **minor** version instead
  (0.4.0 → 0.5.0), the usual convention for pre-1.0 projects. Releasing 1.0.0 is a
  deliberate decision: see below.

## Releases and versioning

Versions follow [Semantic Versioning](https://semver.org/) and are managed by
[release-please](https://github.com/googleapis/release-please) (`.github/workflows/release.yml`):

1. After each merge to `main`, release-please opens or updates a PR titled
   `chore(main): release X.Y.Z`. It bumps [version.txt](version.txt) and adds the
   merged `feat`/`fix` entries to `CHANGELOG.md`.
2. Merge it when you want to release. Unmerged changes keep accumulating in it.
3. On merge, release-please tags `vX.Y.Z` and creates a GitHub Release. The workflow then
   builds the packages for that version and attaches them to the release:
   `sample-users-api-X.Y.Z.tar.gz`, `sample-users-web-X.Y.Z.tar.gz` and `SHA256SUMS`.
   See [deploy/README.md](deploy/README.md) to install them on a VM.

`version.txt` and the tags are the single source of truth for the version. The `version`
fields in `api/pyproject.toml` and `web/package.json` aren't used, which keeps the lock
files stable. The packaged API reports its version at `/health`, and the web app at
`/version.txt`.

**Choosing a version yourself** (for example, the first `1.0.0`): add `Release-As: 1.0.0`
on its own line in the description of the PR you squash-merge. release-please then uses
exactly that version.

**The release PR needs a token secret.** Pull requests opened with the default
`GITHUB_TOKEN` don't trigger other workflows, so the release PR's required checks would
never run. Create a fine-grained personal access token scoped to this repository, with
*Contents* and *Pull requests* set to read and write, then run
`gh secret set RELEASE_PLEASE_TOKEN` and paste the token. (A GitHub App token also works.)

## Repository settings

GitHub doesn't read branch protection from files, so apply the rules above with:

```sh
scripts/setup-github.sh                        # solo: PR + passing checks, no approval
REQUIRED_APPROVALS=1 scripts/setup-github.sh   # team/class: also 1 approving review
```

It configures squash-merge only (PR title as the commit message), auto-deletion of
merged branches, lets Actions open the release PR, and creates a ruleset on `main` that
requires a PR, the four checks above on an up-to-date branch, linear history, resolved
review threads, and blocks force-pushes and deletion. Re-running it updates the ruleset.

## Running the checks locally

```sh
# API (needs the docker compose Postgres running; tests use their own users_test DB)
cd api && uv run ruff check . && uv run ruff format --check . && uv run pytest

# Web
cd web && npm run lint && npm run typecheck && npm test && npm run build

# Packages, exactly as CI builds them (output in ./dist)
scripts/package.sh 0.0.0-local
```

`uv run ruff format .` and `uv run ruff check --fix .` fix most API lint findings.

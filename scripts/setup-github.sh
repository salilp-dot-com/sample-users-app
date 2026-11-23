#!/usr/bin/env bash
# Apply the branching/merging rules from CONTRIBUTING.md to the GitHub repository.
# GitHub doesn't read these from files in the repo, so they're set through its API.
# Safe to re-run: it updates the existing ruleset instead of creating a second one.
#
#   scripts/setup-github.sh                       # repo from the current git remote
#   REQUIRED_APPROVALS=1 scripts/setup-github.sh  # also require one approving review
#
# Requires the GitHub CLI (gh), logged in as a repository admin.
set -euo pipefail

REPO=${REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}
APPROVALS=${REQUIRED_APPROVALS:-0}
RULESET_NAME="main branch protection"

echo "==> Configuring $REPO"

# 1. Merging: squash only, so each PR becomes ONE commit on main whose message is the
#    PR title (a Conventional Commit, which release-please reads). Delete merged branches.
gh api --method PATCH "repos/$REPO" --silent \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true \
  -F allow_update_branch=true \
  -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=PR_BODY
echo "    squash-merge only, PR title as commit message, auto-delete branches"

# 2. Let GitHub Actions open pull requests (release-please's release PR needs this).
gh api --method PUT "repos/$REPO/actions/permissions/workflow" --silent \
  -f default_workflow_permissions=read \
  -F can_approve_pull_request_reviews=true
echo "    Actions may create pull requests; default token is read-only"

# 3. Protect main: no direct pushes, no force-pushes or deletion, linear history,
#    and every change goes through a PR whose CI checks pass on an up-to-date branch.
ruleset=$(
  cat <<JSON
{
  "name": "$RULESET_NAME",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": $APPROVALS,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true,
        "allowed_merge_methods": ["squash"]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "API" },
          { "context": "Web" },
          { "context": "Package / Build packages" },
          { "context": "Conventional PR title" }
        ]
      }
    }
  ]
}
JSON
)

existing=$(gh api "repos/$REPO/rulesets" --jq ".[] | select(.name == \"$RULESET_NAME\") | .id")
if [[ -n "$existing" ]]; then
  gh api --method PUT "repos/$REPO/rulesets/$existing" --input - --silent <<<"$ruleset"
  echo "    updated ruleset '$RULESET_NAME' (#$existing)"
else
  gh api --method POST "repos/$REPO/rulesets" --input - --silent <<<"$ruleset"
  echo "    created ruleset '$RULESET_NAME'"
fi
echo "    main: PR required ($APPROVALS approval(s)), checks API/Web/Package/PR title must pass"

if ! gh secret list --repo "$REPO" | grep -q '^RELEASE_PLEASE_TOKEN'; then
  cat <<'NOTE'

NOTE: secret RELEASE_PLEASE_TOKEN is not set. Release PRs opened with the default token
don't trigger CI, so their required checks never run and the PR can't be merged.
Create a fine-grained token (this repo only; Contents + Pull requests: read & write), then:
    gh secret set RELEASE_PLEASE_TOKEN
See CONTRIBUTING.md → "Releases".
NOTE
fi
echo "==> Done"

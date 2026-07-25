---
name: create-pull-request
description: Use when creating a pull request for the current branch — gathers branch context, generates a PR description following the repo's pull_request_template.md, and opens the PR against main with a Closes reference to its GitHub issue.
user_invocable: true
---

# Create PR

Create a pull request against `main` using the repo's PR template, with a description grounded in the actual diff and a `Closes #<issue>` link.

## Workflow

1. **Base branch is `main`.** It is the only long-lived branch in this repo. Use something else only if the user explicitly asks.

2. **Gather context** (in parallel):
   - `git status -s` — check for uncommitted changes
   - `git diff main...HEAD --stat` — files changed
   - `git log main...HEAD --oneline` — all commits on the branch
   - `git diff main...HEAD --no-color` — full diff; if very large, focus on the most important files first
   - `git rev-parse --abbrev-ref --symbolic-full-name @{u}` — check if the branch tracks a remote
   - Read `.github/pull_request_template.md` from the repo root

3. **Determine the issue number**:
   - Extract from the branch name, which follows `<type>/<issue-number>-<description>`
     (e.g. `feat/42-telegram-notifications` → `42`)
   - If the branch name carries no number, ask the user; check open issues with
     `gh issue list --state open --json number,title`
   - If there is genuinely no issue, proceed without the `Closes` line rather than inventing a number

4. **Draft the PR** using the template from step 2:

   **Title**: `<type>: <concise summary>`, under 70 characters. Type matches the branch type — `feat`, `fix`, `chore`, `refactor`, `docs`, `perf`.

   **Body**: fill in every section of the template from the actual diff:
   - **Description** — what the PR does and why. Focus on the what and why, not a line-by-line walkthrough. Mention notable implementation decisions.
   - **Type of Change** — tick the applicable boxes.
   - **Screenshots and Media** — leave `<!-- Add screenshots here -->` unless the change is visual and you have images.
   - **Test Scenarios** — concrete scenarios grounded in the actual changes ("Sign in via Yandex ID with an account that has no email and confirm the error is surfaced"), never generic filler.
   - **References** — `Closes #<issue-number>`, plus any other issues the user mentions.

   Append a Claude Code session line at the bottom of the body.

5. **Push and create**:

```bash
git push -u origin HEAD
gh pr create --base main --title "<title>" --body "$(cat <<'EOF'
<body>
EOF
)"
```

6. **Return the PR URL** to the user.

## Example Title

```
fix: surface a clear error when Yandex ID returns no email
```

## Guidelines

- Keep the description concise but informative
- Use bullet points when listing multiple changes
- Focus on user-facing impact, not implementation details
- Don't fabricate test scenarios that aren't relevant to the actual changes
- Never put secrets, tokens, or `.env` contents in the PR body

## Common Mistakes

- Targeting a base branch other than `main` — no other long-lived branch exists here
- Summarizing only the latest commit instead of all commits on the branch
- Forgetting to check for an upstream before pushing
- Writing `#42` in the title instead of `Closes #42` in the body
- Wrapping the PR body in a code fence when passing it to `gh pr create`
- Using `--body` without a HEREDOC, so backticks and dollar signs get shell-interpreted

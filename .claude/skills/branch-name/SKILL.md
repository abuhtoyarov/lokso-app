---
name: branch-name
description: Use when starting a new branch or renaming an existing one — produces a branch name in the format `<type>/<issue-number>-<short-description>` that the create-pull-request skill can parse to link the PR to its GitHub issue.
user_invocable: true
---

# Branch Naming

Create branch names following the convention `<type>/<issue-number>-<short-description>`, so the issue number can be extracted later by the `create-pull-request` skill.

## Format

```
<type>/<issue-number>-<short-description>
```

- All lowercase, hyphen-separated
- Issue number is the plain GitHub issue number, no `#` prefix
- Short description is 2–5 words in kebab-case, focused on the _what_, not the _how_
- Branches are always cut from `main`

## Workflow

1. **Determine the type** based on the work being done:
   - `feat` — new functionality
   - `fix` — bug fix
   - `chore` — tooling, deps, config, non-user-facing housekeeping
   - `refactor` — restructuring without behavior change
   - `docs` — documentation only
   - `perf` — performance improvement

2. **Determine the issue number**:
   - If the user gives one, use it
   - If they reference a GitHub issue by URL or title, extract the number:
     `gh issue list --search "<title>" --json number,title`
   - If no issue exists yet, offer to create one — don't invent a number:
     `gh issue create --title "<title>" --body "<description>"`

3. **Write the short description**:
   - 2–5 words in kebab-case
   - Describe the outcome, not the implementation (`add-telegram-notifications`, not `update-bot-service`)
   - Skip filler words (`the`, `a`, `for`)

4. **Assemble and create the branch** from an up-to-date `main`:

```bash
git checkout main && git pull
git checkout -b <type>/<issue-number>-<short-description>
```

5. **Return the branch name** to the user.

## Examples

```
feat/42-telegram-notifications
fix/57-yandex-oauth-missing-email
chore/61-bump-pnpm-version
refactor/70-extract-llm-client-factory
docs/73-local-dev-guide
perf/78-cache-workspace-lookup
```

## Common Mistakes

- Putting the issue number at the end instead of after the type — breaks extraction
- Including the `#` prefix — it has no place in a branch name
- Using underscores or camelCase instead of hyphens
- Branching off anything other than `main` — it's the only long-lived branch
- Inventing an issue number when no issue exists — create the issue instead
- Writing a long, narrative description — keep it scannable
- Using a type that won't match the eventual PR type — pick the type you'd use in the PR title

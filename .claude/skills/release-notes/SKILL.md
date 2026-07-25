---
name: release-notes
description: "Generate release notes for a Lokso release from the commits since the previous tag — filters noise, categorizes by conventional-commit type, and writes the result as a GitHub release body in the four-section format (Features, Enhancements, Bug fixes, Security)."
user_invocable: true
---

# Release Notes Generator

Generate structured release notes for `abuhtoyarov/lokso-app` from the commits between the last release tag and `main`.

## Versioning

Lokso uses semver: `vX.Y.Z`. The current version lives in `package.json` (`"version"`) and is mirrored in `apps/web/package.json`.

- **Patch** (`1.3.1` → `1.3.2`) — bug fixes and security patches only
- **Minor** (`1.3.1` → `1.4.0`) — new user-facing features, backwards-compatible
- **Major** (`1.3.1` → `2.0.0`) — breaking changes to the API or data model

There is one long-lived branch, `main`. Releases are tagged on `main`; there is no separate release branch.

## When to Use

- The user asks for release notes, a changelog, or a GitHub release for Lokso
- A version bump is being prepared

## Steps

### 1. Determine the commit range

```bash
git fetch --tags
PREV=$(git describe --tags --abbrev=0 2>/dev/null)
echo "previous tag: ${PREV:-none}"
```

If a previous tag exists, the range is `$PREV..main`. If this is the first release, use the full history: `git log main --oneline`.

### 2. Fetch commits

```bash
git log ${PREV:+$PREV..}main --no-merges --pretty=format:'%h%n%s%n---BODY---%n%b%n===END==='
```

For a quick scan first:

```bash
git log ${PREV:+$PREV..}main --no-merges --oneline
```

### 3. Filter out noise

Always exclude — mechanical, not user-facing:

| Pattern                                    | Reason                      |
| ------------------------------------------ | --------------------------- |
| `Merge branch '...'`                       | Merge artifact              |
| `fix: merge conflicts`                     | Merge artifact              |
| `Revert "..."` when immediately re-applied | Internal churn              |
| `chore: bump version`                      | The tag carries the version |

### 4. Categorize commits

Map each surviving commit into one of four sections:

| Commit signal                                                                     | Section         |
| --------------------------------------------------------------------------------- | --------------- |
| `feat:` introducing a brand-new screen, flow, or capability                       | ✨ Features     |
| `feat:` improving an existing feature, plus user-visible `refactor:` and `chore:` | ⬆️ Enhancements |
| `fix:`, `fix(scope):`                                                             | 🐞 Bug fixes    |
| CVE upgrades, dependency bumps closing a vulnerability, security hardening        | 🛡️ Security     |

Drop entirely: pure infra `chore:`, dependency bumps with no CVE, internal refactors with no behavioural impact, test-only changes, doc-only changes.

### 5. Format

```markdown
### ✨ Features

#### **Short Feature Name in Title Case**

A 1–3 sentence paragraph describing what the user gets, why it matters, and any notable behaviour. Write in product voice, not commit-message voice.

- Optional nested bullets for sub-capabilities
- Keep them user-facing — what the user can now do

### ⬆️ Enhancements

- One-line description of an improvement to an existing capability

### 🐞 Bug fixes

- Plain-English description of what was broken and is now fixed

### 🛡️ Security

- Upgraded <component> to <version> to mitigate [CVE-XXXX-NNNNN](https://link-to-advisory). Brief impact note.
```

Rules:

- Section headers use `###`, then emoji + **two spaces** + label. Exception: 🛡️ Security uses a single space.
- Features use `####` with the name bolded: `#### **Feature Name**`. Each gets a real paragraph, not a bullet.
- Enhancements, Bug fixes and Security are simple bullets — no commit prefixes, no PR numbers, no issue numbers.
- Do not add a `# Release vX.Y.Z` heading — the tag carries the version.
- Do not insert images; the user adds screenshots manually.
- Drop empty sections entirely.
- Notes are written in Russian — the audience is Russian-speaking users.

### 6. Publish

Bump the version in `package.json` and `apps/web/package.json`, commit, tag, then create the release:

```bash
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z --title "vX.Y.Z" --notes "$(cat <<'EOF'
<release notes markdown>
EOF
)"
```

Always use a HEREDOC with single-quoted `'EOF'` so backticks and dollar signs survive.

## Common Mistakes

- Including issue or PR numbers in bullets — the release body is user-facing
- Adding a `# Release vX.Y.Z` heading — the tag is the version
- Copy-pasting commit subjects verbatim instead of rewriting them into plain product language
- Bulleting features instead of giving each a `#### **Name**` and a paragraph
- Tagging before bumping the version in `package.json`
- Using `--notes` without a HEREDOC, so shell metacharacters corrupt the notes
- Writing the notes in English — the audience is Russian-speaking

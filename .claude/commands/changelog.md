Update CHANGELOG.md with entries for work done in this session.

Steps:
1. Read `CHANGELOG.md` to find the date of the last entry and the current [Unreleased] block
2. Run `git log --oneline --since="$(git log -1 --format=%ai HEAD~20 2>/dev/null || echo '2026-01-01')"` to get recent commits
3. Also review the current conversation to understand what was built/fixed
4. Group changes into categories following Keep a Changelog format:
   - `### Added` — new features
   - `### Changed` — changes to existing functionality
   - `### Fixed` — bug fixes
   - `### Removed` — removed features
5. Update the `## [Unreleased]` section at the top of CHANGELOG.md with the new entries
   - If [Unreleased] already has content, append to the appropriate subsections
   - Do not create a new versioned release — keep everything under [Unreleased]
6. Write the updated CHANGELOG.md

Use concise, user-facing language. Focus on what changed for the user, not implementation details.

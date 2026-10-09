# MentorTrace repository

The main branch carries ongoing MentorTrace development.
The current prerelease version is 1.1.0-dev.3; it is not a stable release.

- Make subsequent development changes on main; a separate dev branch is not required.
- Preserve published version tags and release archives. Publish each new version under a new tag with its own archive rather than replacing an earlier release.
- Preserve the v1.0.0 release directory and its ZIP unchanged.
- Do not modify or publish private source materials or the v0.8 archive.
- Existing audit documents describe the v1.0.0 baseline. They do not certify this development version; rerun applicable audits before release.
- Post-discovery consolidation, final-text delivery, wording and source-fidelity improvements are under validation. New protocols add Language source candidates and formula-source verification records. The original frozen corpora remain unchanged; new development runs use the additional advisor-concerns-v4 snapshot with disclosed training exposure. Behavioral quality has not been established by offline contract tests.

## Service tier authorization

- Default model requests to Standard (`service_tier="default"`), including isolated Codex CLI subprocesses.
- Requests to accelerate work or meet a deadline do not authorize Fast, priority, or another service tier that increases usage charges.
- Enable an increased-usage tier only after explicit user authorization for that tier and its additional usage. Preserve the requested model and reasoning effort independently.
- Any reasoning-effort change, including a downgrade, requires explicit user authorization naming the new effort. Performance goals and ambiguous keywords never authorize settings changes.

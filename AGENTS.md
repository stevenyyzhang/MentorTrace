# MentorTrace development workspace

This directory is the isolated development workspace for MentorTrace v1.1.0.
The current prerelease version is 1.1.0-dev.2; it is not a stable release.

- Make subsequent development changes in this directory.
- Preserve the v1.0.0 release directory and its ZIP unchanged.
- Do not modify or publish private source materials or the v0.8 archive.
- Existing audit documents describe the v1.0.0 baseline. They do not certify this development version; rerun applicable audits before release.
- Post-discovery consolidation, final-text delivery, wording and source-fidelity improvements are under validation. New protocols add Language source candidates and formula-source verification records; both corpora remain unchanged. Behavioral quality has not been established by offline contract tests.

## Service tier authorization

- Default model requests to Standard (`service_tier="default"`), including isolated Codex CLI subprocesses.
- Requests to accelerate work or meet a deadline do not authorize Fast, priority, or another service tier that increases usage charges.
- Enable an increased-usage tier only after explicit user authorization for that tier and its additional usage. Preserve the requested model and reasoning effort independently.
- Any reasoning-effort change, including a downgrade, requires explicit user authorization naming the new effort. Performance goals and ambiguous keywords never authorize settings changes.

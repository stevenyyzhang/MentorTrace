# MentorTrace v1.1.0 workspace

This directory contains the MentorTrace v1.1.0 release source.
It was promoted from 1.1.0-dev.4 on 2026-10-15 at the user's request.

- Make subsequent development changes in this directory.
- Preserve the v1.0.0 release directory and its ZIP unchanged.
- Do not modify or publish private source materials or the v0.8 archive.
- Normal new CLI runs use the reviewed public `corpus/advisor-expression-v1` by default. Only this minimized snapshot is distributed; original historical inputs and private mappings remain private.
- Existing audit documents retain their declared version and scope; rerun applicable release checks. Version promotion does not establish additional behavioral validation.
- Post-discovery consolidation, final-text delivery, wording and source-fidelity improvements are under validation. New protocols add Editor source candidates and formula-source verification records. The original frozen corpora remain unchanged; new development runs use the additional advisor-concerns-v4 snapshot with disclosed training exposure. Behavioral quality has not been established by offline contract tests.

## Service tier authorization

- Default model requests to Standard (`service_tier="default"`), including isolated Codex CLI subprocesses.
- Requests to accelerate work or meet a deadline do not authorize Fast, priority, or another service tier that increases usage charges.
- Enable an increased-usage tier only after explicit user authorization for that tier and its additional usage. Preserve the requested model and reasoning effort independently.
- Any reasoning-effort change, including a downgrade, requires explicit user authorization naming the new effort. Performance goals and ambiguous keywords never authorize settings changes.

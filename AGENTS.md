# MentorTrace working rules

- Start from the files relevant to the user's task; avoid unrelated refactors or broad scans.
- Diagnose with code, configuration and saved evidence before changing behavior. Preserve user changes and frozen historical runs.
- Keep complete source coverage, explicit unknown/unfinished states, Advisor isolation and capacity reserves. Never manufacture missing judgments or silently discard evidence.
- Use the actual authorized model and reasoning effort. Default to Standard (`service_tier="default"`); higher-priced tiers and effort changes require explicit user authorization.
- Reuse valid completed outputs with their real settings and provenance. Inspect uncertain calls before retrying; do not blindly repeat model work.
- Prefer deterministic local checks for hashes, IDs, schemas and exact references. These checks do not certify semantic correctness.
- Keep private manuscripts, source mappings, credentials and run artifacts outside the public distribution. Run `scripts/audit_public_release.py` before publication; do not rely on ignore rules to remove tracked material.
- Run relevant offline tests after changes. Do not invoke review models or publish unless authorized by the current user request.
- New adaptive runs follow `.agents/skills/mentortrace/SKILL.md` and its referenced execution, capacity and delivery contracts. Old frozen protocols retain their original contracts.
- Initial and independent post-processing calls use separate contexts and at most three workers by default; dependent phases wait for complete validated inputs. Both final delivery gates remain required.

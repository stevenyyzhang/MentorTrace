# Citation scope

Default new reviews use `citation_scope: missing_support`. The executable stage contract
is `scripts/review_scope.py`, shared by planning, all independent lanes, Merge/Verify,
drafting and delivery. Flag substantive unsupported claims by identifying the missing
literature/explanation and its insertion point. Do not routinely inspect whether existing
references substantiate claims, map contribution ownership, or request cited full texts.
Do not rewrite those out-of-scope tasks as generic author-confirmation questions.

Preserve manuscript-internal reasoning, ambiguous claims, technical contradictions and
reference-format/numbering issues. Split mixed requests; preserve in-scope components and
record excluded citation audits as outside requested scope using existing disposition fields.
Source-only review preserves the original request as evidence; it does not erase it. This
scope changes what is reviewed, not whether an unverified citation is true or false.

For an explicitly requested citation audit, pass `create --citation-scope citation_audit`
when creating the new run. Never alter a frozen historical run's scope or
retroactively change its evaluation. No external-source access is implied by missing-support
review. Missing-source statements alone are not findings. Source cards remain unchanged.

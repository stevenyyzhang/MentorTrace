"""Explicit citation scope; no keyword-based deletion of review findings."""

INSTRUCTIONS = '''CITATION SCOPE — missing-support review:
Do not routinely verify whether an existing citation is appropriate, whether its source
really proves the adjacent claim, or whether contributions are correctly attributed among
cited papers. Do not open a citation-verification task merely because cited full texts are
unavailable. This scope overrides broader source-library/checklist prompts to audit citations.
Still inspect the manuscript's own reasoning, mathematical validity, internal contradictions,
ambiguous wording and bibliography/numbering defects. A citation does not settle a mathematical
error visible in the manuscript. When a substantive externally grounded claim lacks a citation
or explanation, identify that exact claim and ask for literature supporting the stated point
or an adequate explanation. Do not demand a citation for every routine statement or invent
references. Read surrounding/paragraph-level citations before calling support absent.
For mixed findings, retain the independent manuscript problem and separate the out-of-scope
citation-audit request. Record the latter explicitly as outside requested scope, never as false,
answered or unsupported. Existing source accounting must remain traceable. Source review records
the actual initial request; Merge/Verify apply this scope using their existing dispositions
and reasons. Delivery checks preserve in-scope requirements; they do not reopen excluded citation
audits. Only an explicit user request expands the review to citation verification.
'''


def instructions(protocol):
    return INSTRUCTIONS if protocol.get('citation_scope') == 'missing_support' else ''


def reader_instructions(text, protocol):
    """Replace the legacy conflicting paragraph, not a second parallel rule list."""
    if not instructions(protocol):
        return text
    start = text.find('Check the actual semantic relationship in literature summaries')
    return text[:start] if start >= 0 else text
